
from fastapi import APIRouter
from app.schemas import User, UserId
from typing import List
from app.schemas import Tables
from fastapi import HTTPException
from app.schemas import Tables
# #mport stripe
# import json
# import os
# from fastapi import  render_template, jsonify, request

#stripe.api_key = 'sk_test_IKYCHOAmUhC7IPTdaoVtO58D'

router = APIRouter()

# @router.post('/create-payment-intent')
# def create_payment():
#     try:
#         data = json.loads(request.data)
#         # Create a PaymentIntent with the order amount and currency
#         intent = stripe.PaymentIntent.create(
#             amount=calculate_order_amount(data['items']),
#             currency='usd',
#             # In the latest version of the API, specifying the `automatic_payment_methods` parameter is optional because Stripe enables its functionality by default.
#             automatic_payment_methods={
#                 'enabled': True,
#             },
#         )
#         return jsonify({
#             'clientSecret': intent['client_secret']
#         })
#     except Exception as e:
#         return jsonify(error=str(e)), 403

