from fastapi import APIRouter
from pythainlp.transliterate import romanize
from typing import Literal
from pydantic import BaseModel, Field

router = APIRouter(
    prefix="/transliterate",
    tags=["Transliteration"]
)

class ThaiKaraokePayload(BaseModel):
    text: str = Field(..., description="The Thai text to convert")
    engine: Literal["royin", "paiboon", "thai2rom"] = Field("royin", description="Engine: 'royin' (default), 'paiboon', or 'thai2rom'")

@router.post("/thai-to-karaoke/")
def thai_to_karaoke(payload: ThaiKaraokePayload):
    """
    Convert Thai text to Romanized (Karaoke) script.
    
    Payload:
    - **text**: The Thai text to convert.
    - **engine**: 
        - 'royin'    -> RTGS (ราชบัณฑิต) [Default]
        - 'paiboon'  -> อ่านง่ายแบบคาราโอเกะ
        - 'thai2rom' -> Deep Learning (แม่นยำที่สุด)
    """
    import re
    
    # Romanize using the selected engine
    # Note: 'royin' can sometimes fail to fully romanize complex words without pyicu.
    romanized_text = romanize(payload.text, engine=payload.engine)
    
    # Clean up: Remove any remaining Thai characters ([\u0e00-\u0e7f])
    # This ensures the output is purely Roman script, even if the engine missed some characters.
    clean_romanized = re.sub(r'[\u0e00-\u0e7f]+', '', romanized_text)
    
    return {
        "romanized": clean_romanized,
        "engine": payload.engine
    }
