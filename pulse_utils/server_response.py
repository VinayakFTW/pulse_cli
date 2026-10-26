from fastapi.responses import JSONResponse


def server_response(status_code, message=None, data=None):
    return JSONResponse(
        status_code=status_code,
        content={
            "data": data,
            "message": message,
        },
    )
