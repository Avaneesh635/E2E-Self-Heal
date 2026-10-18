import { useState } from "react";

const UNIT_PRICE = 10;

export function CheckoutQuantity() {
  const [quantity, setQuantity] = useState(1);
  const subtotal = quantity * UNIT_PRICE;

  return (
    <section aria-labelledby="quantity-heading">
      <h2 id="quantity-heading">Quantity</h2>
      <label>
        Quantity
        <input
          id="quantity"
          type="number"
          min="1"
          value={quantity}
          onChange={(event) => setQuantity(Number(event.target.value))}
        />
      </label>
      <p>
        Subtotal <span id="subtotal">${subtotal.toFixed(2)}</span>
      </p>
    </section>
  );
}
