這個專案是要在google sheets的A欄位新增單字時，由gas通知python fastapi，然後由python程式用playwrite去劍橋線上字典抓該單字的資料(發音、詞性、中文意思、英文解釋、例句)，然後將資料寫回google sheets該單字的row的B欄之後的欄位。

流程
- GAS 用 HTTP POST 把 word + row + spreadsheetId + sheetName 傳給 FastAPI
- FastAPI 收到後，用 Playwright 去 Cambridge Dictionary 抓資料
- Python 再用 Google Sheets API 把結果寫回同一列的 B 欄之後

playwright 安裝方式
```
python -m playwright install
```

uvicorn 的執行方式
```
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```