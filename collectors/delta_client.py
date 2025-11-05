"""Delta Exchange API client."""
import time
import hmac
import hashlib
import requests
from typing import Optional, Dict, List, Any
import logging

logger = logging.getLogger(__name__)


class DeltaExchangeClient:
    """Client for Delta Exchange API."""
    
    def __init__(self, api_key: str, api_secret: str, base_url: str = "https://api.delta.exchange"):
        """
        Initialize Delta Exchange client.
        
        Args:
            api_key: API key
            api_secret: API secret
            base_url: Base URL for API
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'api-key': self.api_key
        })
        self._rate_limit_delay = 0.1  # 100ms delay between requests
    
    def _sign_message(self, method: str, path: str, query_string: str, body: str = "") -> str:
        """
        Sign a message for Delta Exchange API.
        
        Args:
            method: HTTP method
            path: API path
            query_string: Query string
            body: Request body
            
        Returns:
            Signature string
        """
        timestamp = str(int(time.time()))
        message = f"{timestamp}{method}{path}{query_string}{body}"
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature, timestamp
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        authenticated: bool = False
    ) -> Dict[str, Any]:
        """
        Make a request to the API.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            params: Query parameters
            data: Request body
            authenticated: Whether to use authentication
            
        Returns:
            API response
        """
        path = f"/v2/{endpoint.lstrip('/')}"
        query_string = ""
        
        if params:
            query_string = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
        
        body = ""
        if data:
            import json
            body = json.dumps(data)
        
        if authenticated:
            signature, timestamp = self._sign_message(method, path, query_string, body)
            self.session.headers.update({
                'signature': signature,
                'timestamp': timestamp
            })
        
        url = f"{self.base_url}{path}"
        if query_string:
            url += f"?{query_string}"
        
        try:
            time.sleep(self._rate_limit_delay)  # Rate limiting
            
            if method.upper() == 'GET':
                response = self.session.get(url)
            elif method.upper() == 'POST':
                response = self.session.post(url, data=body)
            elif method.upper() == 'PUT':
                response = self.session.put(url, data=body)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise
    
    # Public endpoints
    def get_products(self) -> List[Dict]:
        """Get list of all products."""
        return self._make_request('GET', 'products')['result']
    
    def get_product_by_symbol(self, symbol: str) -> Dict:
        """Get product by symbol."""
        return self._make_request('GET', f'products/{symbol}')['result']
    
    def get_ticker(self, symbol: str) -> Dict:
        """Get ticker for a product."""
        return self._make_request('GET', f'tickers/{symbol}')['result']
    
    def get_tickers(self) -> List[Dict]:
        """Get all tickers."""
        return self._make_request('GET', 'tickers')['result']
    
    def get_ohlc(
        self,
        symbol: str,
        resolution: str = "1h",
        start: Optional[int] = None,
        end: Optional[int] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Get OHLC candles.
        
        Args:
            symbol: Product symbol
            resolution: Timeframe (1m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 12h, 1d, 1w)
            start: Start timestamp
            end: End timestamp
            limit: Number of candles
            
        Returns:
            List of OHLC data
        """
        params = {
            'symbol': symbol,
            'resolution': resolution,
            'limit': limit
        }
        if start:
            params['start'] = start
        if end:
            params['end'] = end
        
        return self._make_request('GET', 'history/candles', params=params)['result']
    
    def get_l2_orderbook(self, symbol: str) -> Dict:
        """Get L2 orderbook."""
        return self._make_request('GET', f'l2orderbook/{symbol}')['result']
    
    def get_trades(self, symbol: str, limit: int = 100) -> List[Dict]:
        """Get recent trades."""
        params = {'symbol': symbol, 'limit': limit}
        return self._make_request('GET', 'trades', params=params)['result']
    
    # Authenticated endpoints
    def get_wallet_balances(self) -> List[Dict]:
        """Get wallet balances."""
        return self._make_request('GET', 'wallet/balances', authenticated=True)['result']
    
    def place_order(
        self,
        product_id: int,
        size: float,
        side: str,
        order_type: str = "limit_order",
        limit_price: Optional[float] = None,
        reduce_only: bool = False,
        time_in_force: str = "gtc"
    ) -> Dict:
        """
        Place an order.
        
        Args:
            product_id: Product ID
            size: Order size (positive for buy, negative for sell)
            side: "buy" or "sell"
            order_type: "limit_order" or "market_order"
            limit_price: Limit price (required for limit orders)
            reduce_only: Whether this is a reduce-only order
            time_in_force: "gtc", "ioc", "fok"
            
        Returns:
            Order response
        """
        data = {
            "product_id": product_id,
            "size": abs(size) if side == "buy" else -abs(size),
            "side": side,
            "order_type": order_type,
            "reduce_only": reduce_only,
            "time_in_force": time_in_force
        }
        if limit_price:
            data["limit_price"] = str(limit_price)
        
        return self._make_request('POST', 'orders', data=data, authenticated=True)['result']
    
    def cancel_order(self, order_id: str) -> Dict:
        """Cancel an order."""
        return self._make_request('DELETE', f'orders/{order_id}', authenticated=True)['result']
    
    def get_active_orders(self, product_id: Optional[int] = None) -> List[Dict]:
        """Get active orders."""
        params = {}
        if product_id:
            params['product_id'] = product_id
        return self._make_request('GET', 'orders', params=params, authenticated=True)['result']
    
    def get_positions(self) -> List[Dict]:
        """Get all positions."""
        return self._make_request('GET', 'positions', authenticated=True)['result']
    
    def get_position(self, product_id: int) -> Dict:
        """Get position for a specific product."""
        return self._make_request('GET', f'positions/{product_id}', authenticated=True)['result']
    
    def close_position(self, product_id: int) -> Dict:
        """Close a position."""
        return self._make_request('POST', f'positions/{product_id}/close', authenticated=True)['result']

