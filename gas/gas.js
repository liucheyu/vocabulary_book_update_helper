const FASTAPI_URL = "https://your-domain.com/lookup";
const API_TOKEN = "your-secret-token";

function onEdit(e) {
  const range = e.range;
  const sheet = range.getSheet();

  // 只處理 A 欄
  if (range.getColumn() !== 1) return;

  const row = range.getRow();
  const word = String(range.getValue() || "").trim();

  if (!word) return;

  const payload = {
    spreadsheetId: e.source.getId(),
    sheetName: sheet.getName(),
    row: row,
    word: word
  };

  const options = {
    method: "post",
    contentType: "application/json",
    headers: {
      "X-API-Token": API_TOKEN
    },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  };

  const response = UrlFetchApp.fetch(FASTAPI_URL, options);
  Logger.log(response.getContentText());
}