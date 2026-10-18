import { useState } from "react";

const COUPON_DISCOUNT = 5;

export function CheckoutCoupon() {
  const [code, setCode] = useState("");
  const [discount, setDiscount] = useState(0);

  function applyCoupon() {
    setDiscount(code.trim().toUpperCase() === "SAVE5" ? COUPON_DISCOUNT : 0);
  }

  return (
    <section aria-labelledby="coupon-heading">
      <h2 id="coupon-heading">Coupon</h2>
      <label>
        Coupon code
        <input
          id="coupon-code"
          type="text"
          value={code}
          onChange={(event) => setCode(event.target.value)}
        />
      </label>
      <button id="apply-coupon" type="button" onClick={applyCoupon}>
        Apply
      </button>
      <p>
        Discount <span id="discount">-${discount.toFixed(2)}</span>
      </p>
    </section>
  );
}
