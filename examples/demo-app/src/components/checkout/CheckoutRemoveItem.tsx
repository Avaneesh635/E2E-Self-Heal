import { useState } from "react";

const INITIAL_ITEMS = ["Desk Lamp", "Wall Clock"];

export function CheckoutRemoveItem() {
  const [items, setItems] = useState(INITIAL_ITEMS);

  function removeItem(target: string) {
    setItems((current) => current.filter((item) => item !== target));
  }

  const count = items.length === 1 ? "1 item" : `${items.length} items`;

  return (
    <section aria-labelledby="cart-heading">
      <h2 id="cart-heading">Cart</h2>
      <ul>
        {items.map((item) => (
          <li key={item}>
            {item}
            <button className="remove-item" type="button" onClick={() => removeItem(item)}>
              Remove
            </button>
          </li>
        ))}
      </ul>
      <p>
        Cart <span id="cart-count">{count}</span>
      </p>
    </section>
  );
}
