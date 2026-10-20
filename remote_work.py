from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pulse_tools.remote_request_processor import process_remote_request

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_api_route("/remote-request", process_remote_request, methods=["POST"])