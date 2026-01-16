from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.generate import router as generate_router
from routes.image_to_website import router as image_to_website_router
from routes.pdf_to_website import router as pdf_to_website_router

app = FastAPI(title="WebAgent AI World-Class Website Builder", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

app.include_router(generate_router)
app.include_router(image_to_website_router)
app.include_router(pdf_to_website_router)