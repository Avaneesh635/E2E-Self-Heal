import { useState } from "react";

export function CheckoutPlaceOrder() {
  const [status, setStatus] = useState("Not placed");

  return (
    <section aria-labelledby="place-order-heading">
      <h2 id="place-order-heading">Place order</h2>
      <button id="place-order" type="button" onClick={() => setStatus("Order placed")}>
        Place order
      </button>
      <p>
        Status <span id="order-status">{status}</span>
      </p>
    </section>
  );
}
