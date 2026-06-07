# Pythonコード実行用のDockerイメージ作成

## イメージ作成

```sh
task build
```

## 実行例

```sh
task run python -c '
import polars as pl
df = pl.DataFrame({"Name": ["Alice"]})
print(df)'
```
