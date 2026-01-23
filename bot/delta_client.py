from delta_rest_client import DeltaRestClient

from bot.config import API_KEY, API_SECRET, BASE_URL

try:
    from delta_rest_client import OrderType, TimeInForce
except Exception:  # pragma: no cover - optional enums
    OrderType = None
    TimeInForce = None


class DeltaApi:
    def __init__(self):
        self.client = DeltaRestClient(
            base_url=BASE_URL,
            api_key=API_KEY,
            api_secret=API_SECRET,
        )

    def resolve_product_id(self, symbol, product_id=None):
        if product_id:
            return int(product_id)

        if hasattr(self.client, "get_products"):
            response = self.client.get_products()
            products = response.get("result", response)
        else:
            raise RuntimeError("Delta client missing get_products() method")

        symbol_upper = symbol.upper()
        for product in products:
            if product.get("symbol", "").upper() == symbol_upper:
                return int(product["id"])
            if product.get("product_symbol", "").upper() == symbol_upper:
                return int(product["id"])
        raise RuntimeError(f"Unable to resolve product id for symbol {symbol}")

    def get_candles(self, symbol, resolution, limit):
        if hasattr(self.client, "get_candles"):
            return self.client.get_candles(symbol, resolution, limit)
        raise RuntimeError("Delta client missing get_candles() method")

    def get_position(self, product_id):
        return self.client.get_position(product_id)

    def get_balances(self, asset_id):
        return self.client.get_balances(asset_id)

    def place_order(
        self,
        product_id,
        side,
        size,
        order_type,
        limit_price=None,
        time_in_force=None,
        post_only=False,
        reduce_only=False,
    ):
        payload = {
            "product_id": product_id,
            "size": size,
            "side": side,
            "order_type": order_type,
            "post_only": str(post_only).lower(),
            "reduce_only": str(reduce_only).lower(),
        }
        if limit_price is not None:
            payload["limit_price"] = str(limit_price)
        if time_in_force is not None:
            payload["time_in_force"] = time_in_force
        return self.client.place_order(**payload)

    def place_stop_order(
        self,
        product_id,
        side,
        size,
        stop_price=None,
        limit_price=None,
        order_type="market",
        time_in_force=None,
        is_trailing=False,
        trail_amount=None,
    ):
        payload = {
            "product_id": product_id,
            "size": size,
            "side": side,
            "order_type": order_type,
        }
        if stop_price is not None:
            payload["stop_price"] = str(stop_price)
        if limit_price is not None:
            payload["limit_price"] = str(limit_price)
        if time_in_force is not None:
            payload["time_in_force"] = time_in_force
        if is_trailing:
            payload["isTrailingStopLoss"] = "true"
            if trail_amount is not None:
                payload["trail_amount"] = str(trail_amount)
        return self.client.place_stop_order(**payload)

    def order_type_value(self, value):
        if OrderType is None:
            return value
        return getattr(OrderType, value.upper(), value)

    def tif_value(self, value):
        if TimeInForce is None:
            return value
        return getattr(TimeInForce, value.upper(), value)
