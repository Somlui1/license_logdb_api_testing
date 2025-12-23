if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        ssl_keyfile="./key.pem", 
        ssl_certfile="./cert.pem",
        workers=4
    )