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

    def _extract_ticker(self, data, symbol=None, product_id=None):
        if isinstance(data, dict) and "result" in data:
            data = data["result"]
        if isinstance(data, list):
            if symbol:
                for item in data:
                    if str(item.get("symbol", "")).upper() == str(symbol).upper():
                        return item
            if product_id:
                for item in data:
                    if str(item.get("product_id", "")) == str(product_id):
                        return item
            return data[0] if data else None
        if isinstance(data, dict):
            return data
        return None

    def _fetch_ticker(self, symbol, product_id=None):
        base_url = BASE_URL.rstrip("/") + "/"
        endpoints = [
            (urljoin(base_url, f"v2/tickers/{symbol}"), None),
            (urljoin(base_url, "v2/tickers"), {"symbol": symbol}),
        ]
        if product_id:
            endpoints.append((urljoin(base_url, "v2/tickers"), {"product_id": product_id}))

        last_response = None
        for url, params in endpoints:
            response = requests.get(url, params=params, timeout=10)
            if response.ok:
                payload = response.json()
                ticker = self._extract_ticker(payload, symbol=symbol, product_id=product_id)
                if ticker:
                    return ticker
            last_response = response

        if last_response is not None:
            last_response.raise_for_status()
        raise RuntimeError("Delta ticker request failed without a response")

    def get_ticker(self, symbol, product_id=None):
        try:
            if hasattr(self.client, "get_ticker"):
                try:
                    response = self.client.get_ticker(symbol)
                except TypeError:
                    response = self.client.get_ticker(symbol=symbol)
                ticker = self._extract_ticker(response, symbol=symbol, product_id=product_id)
                if ticker:
                    return ticker
        except Exception:
            pass
        return self._fetch_ticker(symbol, product_id=product_id)

    def get_price(self, symbol, source="mark", product_id=None):
        ticker = self.get_ticker(symbol, product_id=product_id)
        if not isinstance(ticker, dict):
            raise RuntimeError("Ticker response missing data")

        source = (source or "mark").lower()
        if source == "mark":
            keys = ["mark_price", "mark"]
        elif source == "last":
            keys = ["last_price", "last"]
        elif source == "index":
            keys = ["index_price", "spot_price", "spot"]
        else:
            keys = [source]

        for key in keys:
            value = ticker.get(key)
            if value is not None:
                return float(value)

        # Fallback to last price if specific source is missing
        for key in ["last_price", "last", "close"]:
            value = ticker.get(key)
            if value is not None:
                return float(value)

        raise RuntimeError(f"Ticker does not include {source} price")

    def _resolution_candidates(self, resolution):
        candidates = []
        if isinstance(resolution, str):
            value = resolution.strip().lower()
            if value.endswith(("m", "h", "d")) and value[:-1].isdigit():
                factor = {"m": 1, "h": 60, "d": 1440}[value[-1]]
                minutes = int(value[:-1]) * factor
                seconds = minutes * 60
                candidates.extend(
                    [
                        {"value": value, "seconds": seconds},
                        {"value": minutes, "seconds": seconds},
                        {"value": minutes * 60, "seconds": seconds},
                    ]
                )
            elif value.isdigit():
                candidates.extend(self._numeric_resolution_candidates(int(value)))
        elif isinstance(resolution, (int, float)):
            candidates.extend(self._numeric_resolution_candidates(int(resolution)))
        else:
            candidates.append({"value": resolution, "seconds": None})

        seen = set()
        ordered = []
        for item in candidates:
            key = (item["value"], item["seconds"])
            if key not in seen:
                seen.add(key)
                ordered.append(item)
        return ordered

    def _numeric_resolution_candidates(self, value):
        if value <= 0:
            return [{"value": value, "seconds": None}]
        seconds = value
        minutes_as_seconds = value * 60
        return [
            {"value": value, "seconds": minutes_as_seconds},
            {"value": value, "seconds": seconds},
            {"value": minutes_as_seconds, "seconds": minutes_as_seconds},
        ]

    def _fetch_candles(self, symbol, resolution, limit):
        base_url = BASE_URL.rstrip("/") + "/"
        candles_url = urljoin(base_url, "v2/history/candles")
        resolution_candidates = self._resolution_candidates(resolution)
        limit_value = int(limit)
        product_id = None
        try:
            product_id = self.resolve_product_id(symbol)
        except Exception:
            product_id = None

        end_ts = int(time.time())
        candidate_params = []
        for candidate in resolution_candidates:
            res_value = candidate["value"]
            step_seconds = candidate["seconds"]
            base_params = {"resolution": res_value}
            if symbol:
                candidate_params.append({**base_params, "symbol": symbol, "limit": limit_value})
            if product_id:
                candidate_params.append({**base_params, "product_id": product_id, "limit": limit_value})

            if step_seconds:
                start_ts = end_ts - (limit_value * step_seconds)
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
