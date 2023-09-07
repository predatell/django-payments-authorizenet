from .. import PaymentStatus
from ..forms import CreditCardPaymentForm

RESPONSE_STATUS = {"1": PaymentStatus.CONFIRMED, "2": PaymentStatus.REJECTED}


class PaymentForm(CreditCardPaymentForm):
    def clean(self):
        cleaned_data = super().clean()

        if not self.errors:
            if not self.payment.transaction_id:
                data = {
                    "number": cleaned_data.get("number"),
                    "expiration": cleaned_data.get("expiration"),
                    "cvv2": cleaned_data.get("cvv2"),
                }
                print(data)
                response = self.provider.make_transaction(self.payment, data)
                if self.provider.check_response(response):
                    self.payment.transaction_id = self.provider.get_transaction_id(response)
                    self.payment.captured_amount = self.payment.total
                    self.payment.save()
                    self.payment.change_status(PaymentStatus.CONFIRMED)
                else:
                    errors = self.provider.get_error_messages(response)
                    self._errors["__all__"] = self.error_class(errors)
                    self.payment.change_status(PaymentStatus.ERROR, message=errors)
        return cleaned_data
