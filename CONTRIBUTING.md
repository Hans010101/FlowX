# Contributing

1. 从 `main` 创建功能分支。
2. 保持改动小而可验证，不把已冻结的 Playwright 发布器重新接入主界面。
3. 不整体 `safe_dump` 配置文件；设置写回必须保留 YAML 注释和多行 Prompt。
4. 缺来源内容只能删除或软化，禁止新增未经素材支持的来源、机构、日期或数字。
5. 提交前运行 `python -m unittest discover -s tests -v`。

Pull Request 应说明改动目的、用户影响、验证方式以及是否影响发布、安全或配置兼容性。
