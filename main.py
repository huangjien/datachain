import json
import logging

import uvicorn as uvicorn
from decouple import config
from fastapi import FastAPI, Body, requests
from fastapi_utils.tasks import repeat_every
from pydantic import BaseModel

from blockchain import Blockchain
from pages import general_pages_router


class Transaction(BaseModel):
    requester: str
    operator: str
    type: str
    content: str


PORT = config('PORT', default=8080, cast=int)
HOST = config('HOST', default="0.0.0.0")
FORMAT = config('FORMAT', default="%(asctime)s - %(levelname)s - %(message)s")
LOGGING_LEVEL = config('LOGGING_LEVEL', default="INFO")
logging.basicConfig(format=FORMAT, level=LOGGING_LEVEL)

app = FastAPI(name="Deployment", docs_url="/docs", redoc_url="/redoc",
              version='0.1.5', openapi_url="/openapi.json",
              title="Data BlockChain", description="Data in Blockchain")
blockchain = Blockchain()
# app.add_middleware(HTTPSRedirectMiddleware)
# app.add_middleware(
#     TrustedHostMiddleware, allowed_hosts=["localhost", "0.0.0.0", "127.0.0.1"]
# )
app.include_router(general_pages_router)

# the address to other participating members of the network
peers = set()


@app.on_event("startup")
@repeat_every(seconds=5 * 60, wait_first=True)  # every 30 minutes
def backup_local_data():
    dump_data()


def dump_data():
    logging.info("Dumping data...number of blocks: %d", len(blockchain.chain))
    blockchain.dump_data()


@app.post("/data", )
async def set_data(content: dict = Body(...)):
    blockchain.set_data(content)
    blockchain.mine()
    return {"message": f"Data will be added to Block {content}"}


@app.get("/mine")
def mine():
    blockchain.mine()
    return {"message": "New Block mined"}


@app.get("/get_chain")
def get_chain():
    chain_data = []
    for block in blockchain.chain:
        chain_data.append(block.__dict__)
    return {"length": len(chain_data),
            "chain": chain_data}


@app.get("/status")
def status():
    return {"message": "Server is running"}


@app.route('/pending_tx')
def get_pending_tx():
    return json.dumps(blockchain.unconfirmed_data)


def announce_new_block(block):
    for peer in peers:
        try:
            url = "{}add_block".format(peer)
            headers = {'Content-Type': 'application/json'}
            requests.post(url, data=json.dumps(block.__dict__, sort_keys=True), headers=headers)
        except requests.exceptions.ConnectionError:
            logging.warning(f"Connection error: {peer}")


# when shutting down the server, dump the data
app.add_event_handler("shutdown", dump_data)

if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT, log_level="debug")
    # uvicorn.run(app, host=HOST, port=443, log_level="debug",
    #             ssl_keyfile="./key.pem", ssl_certfile="./certificate.pem")
