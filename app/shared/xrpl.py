import os
from typing import Optional

import xrpl
from fastapi import HTTPException
from starlette import status
from xrpl.clients import JsonRpcClient
from xrpl.models import PermissionedDomainSet
from xrpl.wallet import Wallet


class XRPLService:
    def __init__(self):
        self.client = JsonRpcClient(
            os.getenv("XRPL_NODE_URL", "https://s.altnet.rippletest.net:51234/")
        )
        self.service_wallet = self._get_admin_wallet()

    def _get_admin_wallet(self) -> Wallet:
        """Get or create service wallet for domain management"""
        seed = os.getenv("XRPL_SERVICE_WALLET_SEED")
        if seed:
            return Wallet.from_seed(seed)
        else:
            print("XRPL_SERVICE_WALLET_SEED not set")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create_domain(self, domain_name: str) -> str | None:
        """
        Create XRPL permissioned domain

        Args:
            domain_name: Domain name (e.g., "gallery1.roasis.art")

        Returns:
            bool: True if domain creation successful
        """
        try:
            # Create permissioned domain transaction
            # Note: DomainID is omitted to create a new domain
            domain_tx = PermissionedDomainSet(
                account=self.service_wallet.address,
                accepted_credentials=[
                    {
                        "Issuer": self.service_wallet.address,
                        "CredentialType": "ROASIS_GALLARY".encode("utf-8")
                        .hex()
                        .upper(),
                    }
                ],
            )

            # Submit transaction
            response = xrpl.transaction.submit_and_wait(
                domain_tx, self.client, self.service_wallet
            )

            if response.is_successful():
                print("Permissioned domain created successfully")
                print(f"Transaction hash: {response.result.get('hash')}")

                # Extract domain ID from transaction result
                return self._extract_domain_id(response.result)
            else:
                print(f"Domain creation failed: {response.result}")
                return None

        except Exception as e:
            print(f"Error creating domain {domain_name}: {e}")
            return None

    def _extract_domain_id(self, result: dict) -> Optional[str]:
        """Extract domain ID from transaction result"""
        try:
            meta = result.get("meta", {})
            affected_nodes = meta.get("AffectedNodes", [])

            for node in affected_nodes:
                created_node = node.get("CreatedNode", {})
                if created_node.get("LedgerEntryType") == "PermissionedDomain":
                    return created_node.get("LedgerIndex") or created_node.get(
                        "NewFields", {}
                    ).get("DomainID")

            return None
        except Exception as e:
            print(f"Error extracting domain ID: {e}")
            return None
