import requests
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponseForbidden
from django.utils import timezone

import pyxb
from authorizenet.constants import constants
from authorizenet import apicontractsv1
from authorizenet.apicontrollers import createTransactionController, ARBCreateSubscriptionController, ARBCancelSubscriptionController

from .. import PaymentStatus
from .. import RedirectNeeded
from ..core import BasicProvider
from .forms import PaymentForm


class customdate(pyxb.binding.datatypes.date):
    def __new__(cls, *args, **kw):
        # Because of some python, XsdLiteral (pyxb.binding.datatypes line 761)
        # creates a new custom date object, but with inputs like a datetime
        # Then the __new__ of date errors out.
        # So we're going to see if the hour is 12, and minutes, seconds, microseconds and TZ is 0 or empty
        # If so, we remove it
        # Similar issue: https://github.com/AuthorizeNet/sdk-python/issues/145

        if len(args) == 8:
            if args[3] == 12 and all(not bool(x) for x in args[-4:]):
                args = args[:3]
        return super().__new__(cls, *args, **kw)


class AuthorizeNetProvider(BasicProvider):

    def __init__(self, login_id, transaction_key, is_live=False, is_recurring=False, **kwargs):
        self.is_live = is_live
        self.is_recurring = is_recurring
        self.merchantAuth = apicontractsv1.merchantAuthenticationType()
        self.merchantAuth.name = login_id
        self.merchantAuth.transactionKey = transaction_key

    def get_credit_card(self, data):
        credit_card = apicontractsv1.creditCardType()
        credit_card.cardNumber = data.get("number")
        expiration = "%s-%s" % (data.get("expiration").year, data.get("expiration").month)
        credit_card.expirationDate = expiration
        credit_card.cardCode = data.get("cvv2")
        return credit_card

    def get_bill_to_instance(self):
        return apicontractsv1.nameAndAddressType() if self.is_recurring else apicontractsv1.customerAddressType()

    def get_bill_to(self, payment):
        bill_to = self.get_bill_to_instance()
        bill_to.firstName = payment.billing_first_name
        bill_to.lastName = payment.billing_last_name
        return bill_to

    def make_transaction(self, payment, data):
        ControllerClass = self.get_controller_class()
        controller = ControllerClass(self.get_request_instance(payment, data))
        if self.is_live:
            controller.setenvironment(constants.PRODUCTION)
        controller.execute()
        return controller.getresponse()

    def check_response(self, response):
        print(response.messages.resultCode)
        return response.messages.resultCode == "Ok" if self.is_recurring else response.messages.resultCode == "Ok" and response.transactionResponse.responseCode == 1

    def get_controller_class(self):
        return ARBCreateSubscriptionController if self.is_recurring else createTransactionController

    def get_request_instance(self, payment, data):
        if self.is_recurring:
            request = apicontractsv1.ARBCreateSubscriptionRequest()
            request.subscription = self.get_request_type_instance(payment, data)
        else:
            request = apicontractsv1.createTransactionRequest()
            request.transactionRequest = self.get_request_type_instance(payment, data)
        request.merchantAuthentication = self.merchantAuth
        # request.refId = "MerchantID-0001"
        return request

    def get_payment_schedule(self):
        payment_schedule = apicontractsv1.paymentScheduleType()
        payment_schedule.interval = apicontractsv1.paymentScheduleTypeInterval()
        payment_schedule.interval.length = 1
        payment_schedule.interval.unit = 'months'
        payment_schedule.startDate = customdate(timezone.now().date())
        payment_schedule.totalOccurrences = 9999
        return payment_schedule

    def get_request_type_instance(self, payment, data):
        if self.is_recurring:
            request_type = apicontractsv1.ARBSubscriptionType()
            request_type.paymentSchedule = self.get_payment_schedule()
            request_type.name = self.get_transaction_name()
        else:
            request_type = apicontractsv1.transactionRequestType()
            request_type.transactionType = "authCaptureTransaction"
        request_type.amount = payment.total
        request_type.billTo = self.get_bill_to(payment)
        payment_type = apicontractsv1.paymentType()
        payment_type.creditCard = self.get_credit_card(data)
        request_type.payment = payment_type
        request_type.order = self.get_order(payment)
        return request_type

    def get_order(self, payment):
        order = apicontractsv1.orderType()
        invoice_number = "PAYMENT - %s" % payment.pk
        order.invoiceNumber = invoice_number
        order.description = ""
        return order

    def get_transaction_id(self, response):
        return response.subscriptionId if self.is_recurring and response else response.transactionResponse.transId

    def get_error_messages(self, response):
        transaction_errors = ["We have some errors during this transaction... Please check your card number, your Expiration Date and Security Code and try again."]
        if self.is_recurring and response:
            print(response.messages.message)
            for item in response.messages.message:
                transaction_errors.append("%s: %s" % (item.code, item.__dict__.get("text")))
        else:
            try:
                for item in response.transactionResponse.errors:
                    transaction_errors.append("%s: %s" % (item.error.errorCode, item.error.errorText))
            except AttributeError:
                pass
        return transaction_errors

    def get_form(self, payment, data=None):
        if payment.status == PaymentStatus.WAITING:
            payment.change_status(PaymentStatus.INPUT)
        form = PaymentForm(data=data, payment=payment, provider=self)
        if form.is_valid():
            raise RedirectNeeded(payment.get_success_url())
        return form

    def process_data(self, payment, request):
        return HttpResponseForbidden("FAILED")
