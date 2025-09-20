# app/shared/pinata_client.py
import json
from typing import Any, Dict, Optional

import httpx

from app.core.config import settings

PINATA_BASE = "https://api.pinata.cloud/pinning"


def _auth_headers() -> Dict[str, str]:
    # JWT 사용
    return {
        "Authorization": f"Bearer {settings.pinata_jwt}",
    }


async def pin_file_to_ipfs(
    file_bytes: bytes, filename: str, metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Pinata pinFileToIPFS (비동기 버전)
    """
    url = f"{PINATA_BASE}/pinFileToIPFS"
    files = {"file": (filename, file_bytes)}
    if metadata:
        files["pinataMetadata"] = (None, json.dumps(metadata), "application/json")

    print(
        f"Pinning file to IPFS: {filename}, metadata: {metadata}, headers: {_auth_headers()}",
        flush=True,
    )

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(url, headers=_auth_headers(), files=files)
        resp.raise_for_status()
        return resp.json()  # { IpfsHash, PinSize, Timestamp }


async def pin_json_to_ipfs(
    json_obj: Dict[str, Any], name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Pinata pinJSONToIPFS (비동기 버전)
    """
    url = f"{PINATA_BASE}/pinJSONToIPFS"
    payload = {
        "pinataContent": json_obj,
    }
    if name:
        payload["pinataMetadata"] = {"name": name}

    headers = {**_auth_headers(), "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        return resp.json()  # { IpfsHash, PinSize, Timestamp }


# async def pin_file_to_ipfs(file_bytes: bytes, filename: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
#     """
#     Pinata pinFileToIPFS
#     """
#     url = f"{PINATA_BASE}/pinFileToIPFS"
#     files = {
#         "file": (filename, file_bytes)
#     }
#     data = {}
#     if metadata:
#         files["pinataMetadata"] = (None, json.dumps(metadata), "application/json")

#     print(f"Pinning file to IPFS: {filename}, metadata: {metadata}, headers: {_auth_headers()}", flush=True)

#     resp = requests.post(url, headers=_auth_headers(), files=files, data=data, timeout=60)
#     resp.raise_for_status()
#     return resp.json()  # { IpfsHash, PinSize, Timestamp }

# def pin_json_to_ipfs(json_obj: Dict[str, Any], name: Optional[str] = None) -> Dict[str, Any]:
#     """
#     Pinata pinJSONToIPFS
#     """
#     url = f"{PINATA_BASE}/pinJSONToIPFS"
#     payload = {
#         "pinataContent": json_obj,
#     }
#     if name:
#         payload["pinataMetadata"] = {"name": name}

#     resp = requests.post(url, headers={**_auth_headers(), "Content-Type": "application/json"}, json=payload, timeout=60)
#     resp.raise_for_status()
#     return resp.json()  # { IpfsHash, PinSize, Timestamp }
