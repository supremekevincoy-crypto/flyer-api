from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import pikepdf
import io
import copy

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Block data extracted from your LO.pdf and CoBranded.pdf templates ──────────
# These are the exact PieceInfo/PDFlib structures from your saved template files.
# Do NOT edit these unless you re-export from your templates.

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


from decimal import Decimal

def dict_to_pikepdf(obj):
    """Recursively convert a Python dict/list into pikepdf objects."""
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


def stamp_blocks(pdf_bytes: bytes, block_type: str) -> bytes:
    """Stamp LO or CoBranded blocks onto every page of the uploaded PDF."""
    block_type = block_type.lower()
    if block_type == "lo":
        piece_data = LO_PIECE_INFO
    elif block_type == "cobranded":
        piece_data = COBRANDED_PIECE_INFO
    else:
        raise ValueError(f"Unknown block type: {block_type}")

    pdf = pikepdf.open(io.BytesIO(pdf_bytes))
    pikepdf_piece_info = dict_to_pikepdf(piece_data)

    for page in pdf.pages:
        page["/PieceInfo"] = pikepdf_piece_info

    output = io.BytesIO()
    pdf.save(output)
    output.seek(0)
    return output.read()


@app.post("/process")
async def process_flyer(
    file: UploadFile = File(...),
    block_type: str = Form(...),  # "lo" or "cobranded"
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    if block_type.lower() not in ("lo", "cobranded"):
        raise HTTPException(status_code=400, detail="block_type must be 'lo' or 'cobranded'.")

    contents = await file.read()

    try:
        processed = stamp_blocks(contents, block_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")

    # Build output filename: original_name_LO.pdf or original_name_CoBranded.pdf
    base = file.filename.rsplit(".", 1)[0]
    suffix = "LO" if block_type.lower() == "lo" else "CoBranded"
    output_filename = f"{base}_{suffix}.pdf"

    return StreamingResponse(
        io.BytesIO(processed),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{output_filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


@app.get("/health")
def health():
    return {"status": "ok"}
