from urllib.parse import urljoin
import time

import requests
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

    def _fetch_products(self):
        base_url = BASE_URL.rstrip("/") + "/"
        products_url = urljoin(base_url, "v2/products")
        response = requests.get(products_url, timeout=10)
        response.raise_for_status()
        payload = response.json()
        return payload.get("result", payload)

    def _normalize_resolution(self, resolution):
        if isinstance(resolution, (int, float)):
            return int(resolution)
        if isinstance(resolution, str):
            value = resolution.strip().lower()
            if value.endswith("m") and value[:-1].isdigit():
                return int(value[:-1])
            if value.endswith("h") and value[:-1].isdigit():
                return int(value[:-1]) * 60
            if value.endswith("d") and value[:-1].isdigit():
                return int(value[:-1]) * 1440
            if value.isdigit():
                return int(value)
        return resolution

    def _fetch_candles(self, symbol, resolution, limit):
        base_url = BASE_URL.rstrip("/") + "/"
        candles_url = urljoin(base_url, "v2/history/candles")
        normalized_resolution = self._normalize_resolution(resolution)
        limit_value = int(limit)
        product_id = None
        try:
            product_id = self.resolve_product_id(symbol)
        except Exception:
            product_id = None

        resolution_candidates = [normalized_resolution]
        if isinstance(normalized_resolution, int) and normalized_resolution > 0:
            if normalized_resolution < 60:
                resolution_candidates.append(normalized_resolution * 60)

        end_ts = int(time.time())
        candidate_params = []
        for res_value in resolution_candidates:
            base_params = {"resolution": res_value}
            if symbol:
                candidate_params.append({**base_params, "symbol": symbol, "limit": limit_value})
            if product_id:
                candidate_params.append({**base_params, "product_id": product_id, "limit": limit_value})

            seconds_per_step_options = {res_value}
            if isinstance(res_value, int) and res_value > 0:
                seconds_per_step_options.add(res_value * 60)

            for seconds_per_step in seconds_per_step_options:
                start_ts = end_ts - (limit_value * seconds_per_step)
                if symbol:
                    candidate_params.append(
                        {**base_params, "symbol": symbol, "start": start_ts, "end": end_ts}
                    )
                    candidate_params.append(
                        {
                            **base_params,
                            "symbol": symbol,
                            "start": start_ts * 1000,
                            "end": end_ts * 1000,
                        }
                    )
                if product_id:
                    candidate_params.append(
                        {**base_params, "product_id": product_id, "start": start_ts, "end": end_ts}
                    )
                    candidate_params.append(
                        {
                            **base_params,
                            "product_id": product_id,
                            "start": start_ts * 1000,
                            "end": end_ts * 1000,
                        }
                    )

        last_response = None
        for params in candidate_params:
            response = requests.get(candles_url, params=params, timeout=10)
            if response.ok:
                payload = response.json()
                result = payload.get("result", payload)
                if isinstance(result, dict) and "candles" in result:
                    return result["candles"]
                return result
            last_response = response

        if last_response is not None:
            last_response.raise_for_status()
        raise RuntimeError("Delta candles request failed without a response")

    def resolve_product_id(self, symbol, product_id=None):
        if product_id:
            return int(product_id)

        if hasattr(self.client, "get_products"):
            response = self.client.get_products()
            products = response.get("result", response)
        else:
            try:
                products = self._fetch_products()
            except Exception as exc:  # pragma: no cover - network fallback
                raise RuntimeError(
                    "Delta client missing get_products() method. "
                    "Set PRODUCT_ID in your .env or upgrade delta-rest-client."
                ) from exc

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
        try:
            return self._fetch_candles(symbol, resolution, limit)
        except requests.HTTPError as exc:  # pragma: no cover - network fallback
            status = exc.response.status_code if exc.response is not None else "unknown"
            body = exc.response.text[:300] if exc.response is not None else "no response"
            raise RuntimeError(f"Delta candles request failed ({status}): {body}") from exc
        except Exception as exc:  # pragma: no cover - network fallback
            raise RuntimeError(
                "Delta candles request failed. Verify BASE_URL, SYMBOL, and TIMEFRAME."
            ) from exc

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
