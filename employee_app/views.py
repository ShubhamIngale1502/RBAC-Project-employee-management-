from django.shortcuts import render
from rest_framework.views import APIView
from .serializers import DepartmentSerializer,DesignationSerializer,EmployementTypeSerializer,ShiftSerializer,EmployeeSerializer
from rest_framework.permissions import IsAuthenticated
from django.http import JsonResponse
from rest_framework import status
from .models import Department,Designation,EmploymentType,Shift,Employee

class DepartmentView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        departments = Department.objects.all()
        serializer = DepartmentSerializer(departments, many=True)
        return JsonResponse(serializer.data, safe=False)

    def post(self,request):
        try:
            serializer = DepartmentSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return JsonResponse(serializer.data, status=status.HTTP_201_CREATED)
            return JsonResponse(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DesignationView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        designations = Designation.objects.all()
        serializer = DesignationSerializer(designations, many=True)
        return JsonResponse(serializer.data, safe=False)

    def post(self,request):
        try:
            serializer = DesignationSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return JsonResponse(serializer.data, status=status.HTTP_201_CREATED)
            return JsonResponse(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EmployeeView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        employees = Employee.objects.all()
        serializer = EmployeeSerializer(employees, many=True)
        return JsonResponse(serializer.data, safe=False)

    def post(self,request):
        try:
            serializer = EmployeeSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return JsonResponse(serializer.data, status=status.HTTP_201_CREATED)
            return JsonResponse(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

