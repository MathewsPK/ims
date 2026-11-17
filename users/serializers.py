from rest_framework import serializers
from .models import User


class UserSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = User
        fields = ('id', 'email', 'name', 'role', 'role_display',
                  'phone', 'profile_photo', 'is_active', 'date_joined')
        read_only_fields = ('id', 'date_joined')


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ('email', 'name', 'role', 'phone', 'password')

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User.objects.create_user(password=password, **validated_data)
        return user
