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
                    "/I
