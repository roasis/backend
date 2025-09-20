from typing import Optional

import xrpl
from fastapi import HTTPException
from starlette import status
from xrpl.clients import JsonRpcClient
from xrpl.models import PermissionedDomainSet
from xrpl.models.transactions.deposit_preauth import Credential
from xrpl.wallet import Wallet

from app.core.config import settings


class XRPLService:
    def __init__(self):
        self.client = JsonRpcClient(settings.xrpl_rpc_url)
        self.service_wallet = self._get_admin_wallet()

    def _get_admin_wallet(self) -> Wallet:
        """Get or create service wallet for domain management"""
        seed = settings.platform_seed
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
            credential = Credential(
                credential_type="ROASIS_GALLERY".encode('utf-8').hex().upper(),
                issuer=self.service_wallet.address,
            )

            domain_tx = PermissionedDomainSet(
                account=self.service_wallet.address,
                accepted_credentials=[credential]
            )
            print(f"🔍 Transaction created: {domain_tx}")

            # Submit transaction
            print("🔍 Submitting transaction to XRPL...")
            response = xrpl.transaction.submit_and_wait(
                domain_tx, self.client, self.service_wallet
            )
            print(f"🔍 Response received: {type(response)}")
            print(f"🔍 Response: {response}")

            print("🔍 Checking if response is successful...")
            if response.is_successful():
                print("✅ Permissioned domain created successfully")

                # Get transaction hash
                print("🔍 Extracting transaction hash...")
                tx_hash = None
                if hasattr(response, 'result') and isinstance(response.result, dict):
                    tx_hash = response.result.get('hash')
                    print(f"🔍 Hash from response.result: {tx_hash}")
                elif hasattr(response, 'hash'):
                    tx_hash = response.hash
                    print(f"🔍 Hash from response.hash: {tx_hash}")

                if tx_hash:
                    print(f"✅ Transaction hash: {tx_hash}")

                # Extract domain ID from transaction result
                print("🔍 Extracting domain ID...")
                domain_id = self._extract_domain_id(response)
                print(f"🔍 Extracted domain_id: {domain_id}")
                result = domain_id or tx_hash
                print(f"✅ Returning: {result}")
                return result
            else:
                print(f"❌ Domain creation failed: {response}")
                return None

        except Exception as e:
            print(f"❌ Error creating domain {domain_name}: {e}")
            print(f"❌ Error type: {type(e)}")
            import traceback
            print(f"❌ Traceback: {traceback.format_exc()}")
            return None

    def _extract_domain_id(self, result) -> Optional[str]:
        """Extract domain ID from transaction result"""
        try:
            print(f"🔍 _extract_domain_id called with: {type(result)}")
            print(f"🔍 Result value: {result}")

            # Handle different result formats
            if hasattr(result, 'result'):
                result_data = result.result
                print(f"🔍 Using result.result: {result_data}")
            elif isinstance(result, dict):
                result_data = result
                print(f"🔍 Using result as dict: {result_data}")
            else:
                result_data = result.__dict__ if hasattr(result, '__dict__') else {}
                print(f"🔍 Using result.__dict__: {result_data}")

            meta = result_data.get("meta", {}) if isinstance(result_data, dict) else {}
            print(f"🔍 Meta: {meta}")

            affected_nodes = meta.get("AffectedNodes", []) if isinstance(meta, dict) else []
            print(f"🔍 AffectedNodes: {affected_nodes}")

            for i, node in enumerate(affected_nodes):
                print(f"🔍 Processing node {i}: {node}")
                if isinstance(node, dict):
                    created_node = node.get("CreatedNode", {})
                    print(f"🔍 CreatedNode: {created_node}")
                    if isinstance(created_node, dict) and created_node.get("LedgerEntryType") == "PermissionedDomain":
                        domain_id = (created_node.get("LedgerIndex") or created_node.get("NewFields", {}).get("DomainID"))
                        print(f"🔍 Found PermissionedDomain, returning: {domain_id}")
                        return domain_id

            # Fallback: use transaction hash as domain ID
            tx_hash = result_data.get("hash") if isinstance(result_data, dict) else None
            print(f"🔍 Fallback to tx_hash: {tx_hash}")
            return tx_hash

        except Exception as e:
            print(f"❌ Error extracting domain ID: {e}")
            import traceback
            print(f"❌ Traceback: {traceback.format_exc()}")
            return None
