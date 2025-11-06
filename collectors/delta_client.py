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
    
    def __init__(self, api_key: str, api_secret: str, base_url: str = "https://api.india.delta.exchange"):
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
        self._products_cache = None  # Cache for products list
        self._symbol_map = {}  # Cache for symbol variations -> actual symbol
    
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
        # Delta Exchange signature format: {METHOD}{TIMESTAMP}{PATH}{QUERY_STRING}{BODY}
        message = f"{method.upper()}{timestamp}{path}{query_string}{body}"
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature, timestamp
    
    def _normalize_symbol(self, symbol: str) -> str:
        """
        Normalize a symbol to find the correct format used by the exchange.
        Handles variations like SOLUSDT, SOLUSD, SOLUDT, etc.
        
        Args:
            symbol: Symbol to normalize (e.g., 'SOLUSDT', 'SOLUSD')
            
        Returns:
            The actual symbol used by the exchange
            
        Raises:
            ValueError: If symbol cannot be found
        """
        # Check cache first
        if symbol in self._symbol_map:
            return self._symbol_map[symbol]
        
        # If products cache is empty, populate it
        if self._products_cache is None:
            try:
                self._products_cache = self.get_products()
                # Build symbol map from products
                for product in self._products_cache:
                    actual_symbol = product.get('symbol', '')
                    if actual_symbol:
                        # Map the symbol to itself
                        self._symbol_map[actual_symbol] = actual_symbol
                        # Also map common variations
                        symbol_upper = actual_symbol.upper()
                        if symbol_upper.endswith('USDT'):
                            base = symbol_upper[:-4]  # Remove USDT
                            self._symbol_map[f"{base}USD"] = actual_symbol
                            self._symbol_map[f"{base}UDT"] = actual_symbol
                        elif symbol_upper.endswith('USD'):
                            base = symbol_upper[:-3]  # Remove USD
                            self._symbol_map[f"{base}USDT"] = actual_symbol
                            self._symbol_map[f"{base}UDT"] = actual_symbol
                        elif symbol_upper.endswith('UDT'):
                            base = symbol_upper[:-3]  # Remove UDT
                            self._symbol_map[f"{base}USD"] = actual_symbol
                            self._symbol_map[f"{base}USDT"] = actual_symbol
            except Exception as e:
                logger.warning(f"Could not load products for symbol normalization: {e}")
                # If we can't load products, try direct lookup
                return symbol
        
        # Try exact match first
        symbol_upper = symbol.upper()
        if symbol_upper in self._symbol_map:
            normalized = self._symbol_map[symbol_upper]
            self._symbol_map[symbol] = normalized  # Cache original symbol too
            return normalized
        
        # Try case-insensitive search in products
        for product in self._products_cache:
            product_symbol = product.get('symbol', '')
            if product_symbol.upper() == symbol_upper:
                self._symbol_map[symbol] = product_symbol
                self._symbol_map[symbol_upper] = product_symbol
                return product_symbol
        
        # Generate variations and search
        variations = [symbol_upper]
        
        # Common variations
        if symbol_upper.endswith('USDT'):
            base = symbol_upper[:-4]
            variations.extend([f"{base}USD", f"{base}UDT"])
        elif symbol_upper.endswith('USD'):
            base = symbol_upper[:-3]
            variations.extend([f"{base}USDT", f"{base}UDT"])
        elif symbol_upper.endswith('UDT'):
            base = symbol_upper[:-3]
            variations.extend([f"{base}USD", f"{base}USDT"])
        
        # Search for variations in products
        for variation in variations:
            for product in self._products_cache:
                product_symbol = product.get('symbol', '')
                if product_symbol.upper() == variation:
                    self._symbol_map[symbol] = product_symbol
                    self._symbol_map[symbol_upper] = product_symbol
                    # Cache all variations
                    for v in variations:
                        self._symbol_map[v] = product_symbol
                    logger.info(f"Symbol '{symbol}' normalized to '{product_symbol}'")
                    return product_symbol
        
        # If still not found, cache the failure and return original
        logger.warning(f"Could not normalize symbol '{symbol}', using as-is")
        self._symbol_map[symbol] = symbol
        return symbol
    
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
            # For signature, query string must include '?' prefix if present
            signature_query_string = f"?{query_string}" if query_string else ""
            signature, timestamp = self._sign_message(method, path, signature_query_string, body)
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
        normalized_symbol = self._normalize_symbol(symbol)
        try:
            return self._make_request('GET', f'products/{normalized_symbol}', authenticated=True)['result']
        except requests.exceptions.RequestException:
            # If normalized symbol fails, try original
            if normalized_symbol != symbol:
                logger.warning(f"Failed with normalized symbol '{normalized_symbol}', trying original '{symbol}'")
                return self._make_request('GET', f'products/{symbol}', authenticated=True)['result']
            raise
    
    def get_ticker(self, symbol: str) -> Dict:
        """Get ticker for a product."""
        normalized_symbol = self._normalize_symbol(symbol)
        try:
            return self._make_request('GET', f'tickers/{normalized_symbol}', authenticated=True)['result']
        except requests.exceptions.RequestException:
            # If normalized symbol fails, try original
            if normalized_symbol != symbol:
                logger.warning(f"Failed with normalized symbol '{normalized_symbol}', trying original '{symbol}'")
                return self._make_request('GET', f'tickers/{symbol}', authenticated=True)['result']
            raise
    
    def get_tickers(self) -> List[Dict]:
        """Get all tickers."""
        return self._make_request('GET', 'tickers', authenticated=True)['result']
    
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
            start: Start timestamp (auto-calculated if not provided)
            end: End timestamp (defaults to now if not provided)
            limit: Number of candles (used to calculate start if not provided)
            
        Returns:
            List of OHLC data
        """
        # Calculate end time if not provided (default to now)
        if end is None:
            end = int(time.time())
        
        # Calculate start time if not provided (based on limit and resolution)
        if start is None:
            # Resolution to seconds mapping
            resolution_seconds = {
                '1m': 60,
                '5m': 300,
                '15m': 900,
                '30m': 1800,
                '1h': 3600,
                '2h': 7200,
                '4h': 14400,
                '6h': 21600,
                '12h': 43200,
                '1d': 86400,
                '1w': 604800
            }
            seconds_per_candle = resolution_seconds.get(resolution, 3600)  # Default to 1h
            start = end - (limit * seconds_per_candle)
        
        normalized_symbol = self._normalize_symbol(symbol)
        params = {
            'symbol': normalized_symbol,
            'resolution': resolution,
            'start': start,
            'end': end,
            'limit': limit
        }
        
        try:
            return self._make_request('GET', 'history/candles', params=params, authenticated=True)['result']
        except requests.exceptions.RequestException:
            # If normalized symbol fails, try original
            if normalized_symbol != symbol:
                logger.warning(f"Failed with normalized symbol '{normalized_symbol}', trying original '{symbol}'")
                params['symbol'] = symbol
                return self._make_request('GET', 'history/candles', params=params, authenticated=True)['result']
            raise
    
    def get_l2_orderbook(self, symbol: str) -> Dict:
        """Get L2 orderbook."""
        normalized_symbol = self._normalize_symbol(symbol)
        try:
            return self._make_request('GET', f'l2orderbook/{normalized_symbol}', authenticated=True)['result']
        except requests.exceptions.RequestException:
            # If normalized symbol fails, try original
            if normalized_symbol != symbol:
                logger.warning(f"Failed with normalized symbol '{normalized_symbol}', trying original '{symbol}'")
                return self._make_request('GET', f'l2orderbook/{symbol}', authenticated=True)['result']
            raise
    
    def get_trades(self, symbol: str, limit: int = 100) -> List[Dict]:
        """Get recent trades."""
        normalized_symbol = self._normalize_symbol(symbol)
        params = {'symbol': normalized_symbol, 'limit': limit}
        try:
            return self._make_request('GET', 'trades', params=params)['result']
        except requests.exceptions.RequestException:
            # If normalized symbol fails, try original
            if normalized_symbol != symbol:
                logger.warning(f"Failed with normalized symbol '{normalized_symbol}', trying original '{symbol}'")
                params['symbol'] = symbol
                return self._make_request('GET', 'trades', params=params)['result']
            raise
    
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
    
    def get_positions(self, product_id: Optional[int] = None, underlying_asset_symbol: Optional[str] = None) -> List[Dict]:
        """
        Get positions.
        
        Args:
            product_id: Optional product ID filter
            underlying_asset_symbol: Optional underlying asset symbol filter
            
        Returns:
            List of positions
        """
        params = {}
        if product_id:
            params['product_id'] = product_id
        if underlying_asset_symbol:
            params['underlying_asset_symbol'] = underlying_asset_symbol
        
        # If no params provided, return empty list (API requires at least one)
        if not params:
            return []
        
        return self._make_request('GET', 'positions', params=params, authenticated=True)['result']
    
    def get_position(self, product_id: int) -> Dict:
        """Get position for a specific product."""
        return self._make_request('GET', f'positions/{product_id}', authenticated=True)['result']
    
    def close_position(self, product_id: int) -> Dict:
        """Close a position."""
        return self._make_request('POST', f'positions/{product_id}/close', authenticated=True)['result']

