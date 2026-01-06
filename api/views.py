from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from main.models import Lead, LeadPhoneNumbers, LeadEmails, LeadContactNames
from sales.forms import LeadPhoneNumberForm, LeadEmailForm, LeadContactNameForm

@api_view(['POST'])
def add_phone_number(request):
    form = LeadPhoneNumberForm(request.data)
    if form.is_valid():
        phone_number = form.save(commit=False)
        phone_number.lead_id = request.data.get('lead_id')
        phone_number.sheet_id = request.data.get('sheet_id')  # Pass the correct sheet ID
        phone_number.save()
        return Response({"message": "Phone number added successfully", "phone_number": phone_number.value}, status=status.HTTP_201_CREATED)
    return Response({"errors": form.errors}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def add_email(request):
    form = LeadEmailForm(request.data)
    if form.is_valid():
        email = form.save(commit=False)
        email.lead_id = request.data.get('lead_id')
        email.sheet_id = request.data.get('sheet_id')
        email.save()
        return Response({"message": "Email added successfully", "email": email.value}, status=status.HTTP_201_CREATED)
    return Response({"errors": form.errors}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def add_contact_name(request):
    form = LeadContactNameForm(request.data)
    if form.is_valid():
        contact_name = form.save(commit=False)
        contact_name.lead_id = request.data.get('lead_id')
        contact_name.sheet_id = request.data.get('sheet_id')
        contact_name.save()
        return Response({"message": "Contact name added successfully", "contact_name": contact_name.value}, status=status.HTTP_201_CREATED)
    return Response({"errors": form.errors}, status=status.HTTP_400_BAD_REQUEST)
