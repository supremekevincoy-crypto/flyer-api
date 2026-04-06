from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import pikepdf
import io
import zipfile
from decimal import Decimal

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

LO_PIECE_INFO = {
    "/PDFlib": {
        "/LastModified": "D:20250619143153-07'00'",
        "/Private": {
            "/Blocks": {
                "/Disclaimer": {
                    "/ID": 6,
                    "/Name": "/Disclaimer",
                    "/Rect": [45.16, 33.38, 552.44, 74.61],
                    "/Subtype": "/Text",
                    "/Type": "/Block",
                    "/backgroundcolor": ["/None"],
                    "/bordercolor": ["/None"],
                    "/fitmethod": "/auto",
                    "/fontname": "ARIALN",
                    "/fontsize": 6,
                    "/strokecolor": ["/DeviceCMYK", [0.0, 0.0, 0.0, 0.0]],
                    "/textflow": True,
                    "/wordspacing": -0.0180054,
                },
                "/LO_Block": {
                    "/ID": 7,
                    "/Name": "/LO_Block",
                    "/Rect": [45.82, 80.51, 327.93, 181.31],
                    "/Subtype": "/PDF",
                    "/Type": "/Block",
                    "/backgroundcolor": ["/None"],
                    "/bordercolor": ["/None"],
                    "/fitmethod": "/auto",
                    "/position": [0, 100],
                },
                "/LO_Logo": {
                    "/ID": 5,
                    "/Name": "/LO_Logo",
                    "/Rect": [354.11, 99.49, 556.36, 170.84],
                    "/Subtype": "/Image",
                    "/Type": "/Block",
                    "/backgroundcolor": ["/None"],
                    "/bordercolor": ["/None"],
                    "/dpi": [300],
                    "/fitmethod": "/auto",
                    "/position": [0, 100],
                    "/scale": [2],
                },
            },
            "/PluginVersion": "6.1",
            "/Version": 6,
        },
    }
}

COBRANDED_PIECE_INFO = {
    "/PDFlib": {
        "/LastModified": "D:20250619143206-07'00'",
        "/Private": {
            "/Blocks": {
                "/BP_Block": {
                    "/ID": 4,
                    "/Name": "/BP_Block",
                    "/Rect": [36, 81.82, 288.65, 182.17],
                    "/Subtype": "/PDF",
                    "/Type": "/Block",
                    "/backgroundcolor": ["/None"],
                    "/bordercolor": ["/None"],
                    "/fitmethod": "/auto",
                    "/position": [50],
                },
                "/Disclaimer": {
                    "/ID": 2,
                    "/Name": "/Disclaimer",
                    "/Rect": [36, 30.11, 555.06, 75.27],
                    "/Subtype": "/Text",
                    "/Type": "/Block",
                    "/backgroundcolor": ["/None"],
                    "/bordercolor": ["/None"],
                    "/fitmethod": "/auto",
                    "/fontname": "ARIALN",
                    "/fontsize": 6,
                    "/strokecolor": ["/DeviceCMYK", [0.0, 0.0, 0.0, 0.0]],
                    "/textflow": True,
                    "/wordspacing": -0.0180054,
                },
                "/LO_Block": {
                    "/ID": 3,
                    "/Name": "/LO_Block",
                    "/Rect": [296.51, 81.82, 575.35, 181.96],
                    "/Subtype": "/PDF",
                    "/Type": "/Block",
                    "/backgroundcolor": ["/None"],
                    "/bordercolor": ["/None"],
                    "/fitmethod": "/auto",
                    "/position": [0, 100],
                },
                "/LO_Logo": {
                    "/ID": 1,
                    "/Name": "/LO_Logo",
                    "/Rect": [493.68, 156.43, 575.42, 182.26],
                    "/Subtype": "/Image",
                    "/Type": "/Block",
                    "/backgroundcolor": ["/None"],
                    "/bordercolor": ["/None"],
                    "/dpi": [300],
                    "/fitmethod": "/auto",
                    "/position": [0, 100],
                    "/scale": [2],
                },
            },
            "/PluginVersion": "6.1",
            "/Version": 6,
        },
    }
}


def dict_to_pikepdf(obj):
    if isinstance(obj, dict):
        d = pikepdf.Dictionary()
        for k, v in obj.items():
            d[k] = dict_to_pikepdf(v)
        return d
    elif isinstance(obj, list):
        return pikepdf.Array([dict_to_pikepdf(i) for i in obj])
    elif isinstance(obj, bool):
        return obj
    elif isinstance(obj, int):
        return obj
    elif isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, str):
        if obj.startswith("/"):
            return pikepdf.Name(obj)
        return obj
    return obj


def stamp_blocks(pdf_bytes: bytes, piece_data: dict) -> bytes:
    pdf = pikepdf.open(io.BytesIO(pdf_bytes))
    pikepdf_piece_info = dict_to_pikepdf(piece_data)
    for page in pdf.pages:
        page["/PieceInfo"] = pikepdf_piece_info
    output = io.BytesIO()
    pdf.save(output)
    output.seek(0)
    return output.read()


@app.post("/process")
async def process_flyer(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    contents = await file.read()
    base = file.filename.rsplit(".", 1)[0]

    try:
        lo_pdf = stamp_blocks(contents, LO_PIECE_INFO)
        cobranded_pdf = stamp_blocks(contents, COBRANDED_PIECE_INFO)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{base}_LO.pdf", lo_pdf)
        zf.writestr(f"{base}_CoBranded.pdf", cobranded_pdf)
    zip_buffer.seek(0)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{base}_blocks.zip"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


@app.get("/health")
def health():
    return {"status": "ok"}
