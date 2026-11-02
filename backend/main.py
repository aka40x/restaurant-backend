from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from responses import success_response

app = FastAPI(title="Restaurant Management API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Moi nguoi chi them DUNG 1 DONG include_router cua module minh o day (tranh xung dot khi merge).
# Vi du:
# from routers import auth_router
# app.include_router(auth_router.router)


@app.get("/")
def root(request: Request):
    return success_response(request, "Restaurant API is running")
