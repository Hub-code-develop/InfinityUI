#!/usr/bin/env python3
"""把 nupkg 里的 nuspec 补上 <owners>。

为什么需要它：
Trusted Publishing 换到的临时 API Key 权限绑定在 policy 的 Policy Owner 上。
policy 的 Owner 选的是 nuget.org 组织时，包必须以同一个 owner 发布，否则
push 会返回 403 "The specified API key is invalid, has expired, or does not
have permission to access the specified package"。

dotnet pack 的 MSBuild 属性（PackageOwners / Owners）在当前 SDK 下不会写进
nuspec，所以这里在打包后直接改写 nuspec。

用法：python3 scripts/set_owner.py <nupkg路径> <owner>
"""
import os
import re
import sys
import zipfile


def set_owner(nupkg_path: str, owner: str) -> None:
    tmp_path = nupkg_path + ".tmp"
    patched = False

    with zipfile.ZipFile(nupkg_path, "r") as source:
        with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as target:
            for item in source.infolist():
                data = source.read(item.filename)
                if item.filename.lower().endswith(".nuspec"):
                    text = data.decode("utf-8-sig")
                    # nuspec 的 metadata 子元素有 schema 顺序要求：
                    # id → version → title → authors → owners → requireLicenseAcceptance → ...
                    # owners 必须紧跟在 authors 之后；放到 </metadata> 前会被 NuGet 忽略。
                    text = re.sub(r"\s*<owners>.*?</owners>", "", text, flags=re.S)
                    if "<owners>" not in text:
                        if "</authors>" in text:
                            text = text.replace(
                                "</authors>",
                                f"</authors>\n    <owners>{owner}</owners>",
                                1,
                            )
                        else:
                            text = text.replace(
                                "</metadata>",
                                f"  <owners>{owner}</owners>\n  </metadata>",
                                1,
                            )
                    data = text.encode("utf-8")
                    patched = True
                target.writestr(item, data)

    os.replace(tmp_path, nupkg_path)

    if not patched:
        raise SystemExit(f"未在 {nupkg_path} 中找到 nuspec")


def main() -> None:
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)

    owner = sys.argv[2]
    for path in sys.argv[1:]:
        if path.endswith(".nupkg"):
            set_owner(path, owner)
            print(f"owner 已设置为 {owner}: {path}")


if __name__ == "__main__":
    main()
