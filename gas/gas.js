function mySheetUpdate(e) {
  try {
    const range = e.range;

    if (!range.getSheet) return;

    const sheet = range.getSheet();

    if (sheet.getName() !== "dic") return;

    if (range.getColumn() !== 1) return;

    const row = range.getRow();
    const raw = String(range.getValue() || "");
    const phrase = normalizePhrase(raw);
    if (!phrase) return;

    if (!isValidWordOrPhraseFormat(phrase)) {
      Logger.log("Skip invalid format: " + phrase);
      return;
    }

    const FASTAPI_URL = "https://your-domain.com/lookup";
    const API_TOKEN = "your-secret-token";

    if (!existsInDictionary(phrase)) {
      Logger.log("Skip not found in dictionary: " + phrase);
      return;
    }

    const payload = {
      spreadsheetId: e.source.getId(),
      sheetName: sheet.getName(),
      row: row,
      word: phrase,
    };

    const options = {
      method: "post",
      contentType: "application/json",
      headers: { "X-API-Token": API_TOKEN },
      payload: JSON.stringify(payload),
      muteHttpExceptions: true,
    };

    Logger.log("Would send to API: " + JSON.stringify(payload));

    // const res = UrlFetchApp.fetch(FASTAPI_URL, options);
    // Logger.log(res.getResponseCode() + " " + res.getContentText());
  } catch (err) {
    Logger.log("Error in onEdit: " + err);
  }
}

// 去除前後空格和兩個以上的空格
function normalizePhrase(s) {
  return s.trim().replace(/\s+/g, " ");
}

function isValidWordOrPhraseFormat(s) {
  // 允許英文字母、空白、連字號、撇號（含 ’）
  if (!/^[A-Za-z][A-Za-z\s'\-’]{0,79}$/.test(s)) return false;
  const tokenCount = s.split(" ").filter(Boolean).length;
  // 單字或慣用語，限制 1~6 詞可自行調整
  return tokenCount >= 1 && tokenCount <= 6;
}

function existsInDictionary(phrase) {
  //const cache = CacheService.getScriptCache();
  const key = "dict:" + phrase.toLowerCase();
  // const cached = cache.get(key);
  // if (cached !== null) return cached === "1";

  const slug = encodeURIComponent(phrase.toLowerCase());
  const url =
    "https://dictionary.cambridge.org/dictionary/english-chinese-traditional/" +
    slug;

  const res = UrlFetchApp.fetch(url, { muteHttpExceptions: true });
  const code = res.getResponseCode();
  const html = res.getContentText();

  // 依實際頁面可再微調判斷字串
  const ok =
    code === 200 &&
    html.indexOf("entry-body__el") !== -1 &&
    html.indexOf("did you mean") === -1 &&
    html.indexOf("No results") === -1;

  //cache.put(key, ok ? '1' : '0', 21600); // 6 小時
  return ok;
}

function testFetch() {
  const res = UrlFetchApp.fetch(
    "https://dictionary.cambridge.org/dictionary/english-chinese-traditional/hello",
    { muteHttpExceptions: true },
  );

  Logger.log("res: " + JSON.stringify(res));
}
