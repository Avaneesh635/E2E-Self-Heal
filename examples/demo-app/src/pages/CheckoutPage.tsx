import { CheckoutCoupon } from "../components/checkout/CheckoutCoupon";
import { CheckoutPlaceOrder } from "../components/checkout/CheckoutPlaceOrder";
import { CheckoutQuantity } from "../components/checkout/CheckoutQuantity";
import { CheckoutRemoveItem } from "../components/checkout/CheckoutRemoveItem";

export function CheckoutPage() {
  return (
    <section aria-labelledby="checkout-heading">
      <h1 id="checkout-heading">Checkout</h1>
      <CheckoutQuantity />
      <CheckoutCoupon />
      <CheckoutRemoveItem />
      <CheckoutPlaceOrder />
    </section>
  );
}
