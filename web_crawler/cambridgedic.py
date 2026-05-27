import asyncio
from datetime import datetime
from fastapi import FastAPI, Header, HTTPException
from flask import json
from pydantic import BaseModel
from typing import Optional
from playwright.async_api import async_playwright
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

API_TOKEN = ""


class LookupRequest(BaseModel):
    spreadsheetId: str
    sheetName: str
    row: int
    word: str


app = FastAPI()

@app.get("/alive")
async def alive():
    return {"ok": True, "timestamp": datetime.now().isoformat()}

@app.post("/lookup")
async def lookup_word(payload: LookupRequest, x_api_token: Optional[str] = Header(None)):
    if x_api_token != API_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid token")

    word_data = await crawl_cambridge(payload.word)

    write_word_to_sheet(payload, word_data)

    return {
        "ok": True,
        "word": payload.word,
        "row": payload.row,
        "data": word_data
    }


async def crawl_cambridge(word: str) -> list:
    url = f"https://dictionary.cambridge.org/dictionary/english-chinese-traditional/{word}"
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, wait_until = "domcontentloaded", timeout=60000)

        # 考慮到多態，先都抓
        items = []
        bodys = await page.query_selector_all(".entry-body__el")
        
        for body in bodys:            
            pronunciation = ""
            part_of_speech = ""
                       

            try:
                pronunciation = await (await (await body.query_selector(".us.dpron-i")).query_selector(".pron.dpron")).inner_text()
            except Exception as e:
                print(f"Error fetching pronunciation: {e}")
                pass

            try:
                pos = await body.query_selector_all(".pos.dpos")
                part_of_speech = ""
                if len(pos) > 1:
                    part_of_speech =  await pos[1].inner_text()
                else:
                    part_of_speech =  await pos[0].inner_text()
            except Exception as e:
                print(f"Error fetching part of speech: {e}")
                pass

            # 同一詞態還會有多個意思，都抓              
            means = await body.query_selector_all(".def-block.ddef_block")
           
            for mean in means:
                try:
                    chinese_meaning = ""
                    english_definition = ""
                    example_sentence = ""
                    
                    chinese_block = await mean.query_selector("span[class='trans dtrans dtrans-se  break-cj']")
                    
                    if not chinese_block:
                        continue
                    chinese_meaning = await chinese_block.inner_text()                    
                    english_definition = await (await mean.query_selector(".def.ddef_d")).inner_text()
                    example_block = await mean.query_selector(".examp.dexamp")
                    # 例句用換行符分隔
                    if example_block:
                        example_sentence = "\n".join([await e.inner_text() for e in await mean.query_selector_all(".examp.dexamp")])

                    items.append({
                        "word": word,
                        "pronunciation": pronunciation,
                        "part_of_speech": part_of_speech,
                        "chinese_meaning": chinese_meaning,
                        "english_definition": english_definition,
                        "example_sentence": example_sentence
                    })
                except Exception as e:
                    print(f"Error fetching meaning: {e}")
                    continue
    await browser.close()
    return items

SERVICE_ACCOUNT_FILE = "service_account.json"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

def write_word_to_sheet(payload: LookupRequest, word_datas):
    credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)

    service = build("sheets", "v4", credentials=credentials)
    
    #range_name = f"{payload.sheetName}!A{payload.row}"
    values = []
    for word_data in word_datas:
        values.append([
            word_data.get("word", ""),
            word_data.get("pronunciation", ""),
            word_data.get("part_of_speech", ""),
            word_data.get("chinese_meaning", ""),
            word_data.get("english_definition", ""),
            word_data.get("example_sentence", "")
        ])

    if not values:
        print("No data to write.")
        return
    
    rows_to_insert = len(values) - 1

        # 2) 先拿 sheetId（insertDimension 需要 numeric sheetId）
    ss = service.spreadsheets().get(spreadsheetId=payload.spreadsheetId).execute()
    sheet_id = None
    for s in ss.get("sheets", []):
        if s.get("properties", {}).get("title") == payload.sheetName:
            sheet_id = s.get("properties", {}).get("sheetId")
            break
    if sheet_id is None:
        raise ValueError("sheetName not found")

    # 3) 檢查下一列是否有資料
    next_row_range = f"{payload.sheetName}!A{payload.row + 1}"
    next_row_resp = service.spreadsheets().values().get(
        spreadsheetId=payload.spreadsheetId,
        range=next_row_range
    ).execute()
    next_row_values = next_row_resp.get("values", [])
    next_row_has_data = bool(next_row_values and any(cell.strip() for cell in next_row_values[0]))

    # 4) 有資料才插入 rows_to_insert 列
    if rows_to_insert > 0 and next_row_has_data:
        # 注意：GridRange 是 0-based，startIndex 對應「payload.row 的下一列」
        service.spreadsheets().batchUpdate(
            spreadsheetId=payload.spreadsheetId,
            body={
                "requests": [
                    {
                        "insertDimension": {
                            "range": {
                                "sheetId": sheet_id,
                                "dimension": "ROWS",
                                "startIndex": payload.row,                  # row+1 的 0-based
                                "endIndex": payload.row + rows_to_insert
                            },
                            "inheritFromBefore": True
                        }
                    }
                ]
            }
        ).execute()

    # 5) 從 payload.row 開始寫入多列
    range_name = f"{payload.sheetName}!A{payload.row}"
    result = service.spreadsheets().values().update(
        spreadsheetId=payload.spreadsheetId,
        range=range_name,
        valueInputOption="RAW",
        body={"values": values}
    ).execute()

    print(f"{result.get('updatedCells')} cells updated.")



targetSheetId = ""

def main():
    # import uvicorn
    # uvicorn.run(app, host="0.0.0.0", port=8000)
    items = asyncio.run(crawl_cambridge("hello"))
    write_word_to_sheet(LookupRequest(
        spreadsheetId=targetSheetId,
        sheetName="Sheet1",
        row=2,
        word="hello"
    ), items)
    

if __name__ == "__main__":
    main()