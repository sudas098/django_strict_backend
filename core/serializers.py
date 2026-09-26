from rest_framework import serializers

from core.models import CustomUser


class UserSerializer(serializers.ModelSerializer[CustomUser]):
    """Public read-only user representation"""
    class Meta:
        model = CustomUser
        fields = [
            "id",
            "email",
            "is_active",
            "date_joined"
        ]
        read_only_fields = fields

class UserRegistrationSerializer(serializers.ModelSerializer[CustomUser]):
    """Registration input serializer enforcing password validation"""
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        max_length=128,
        style={"input_type": "password"}
    )

    class Meta:
        model = CustomUser
        fields = ["email", "password"]

    def validate_email(self, value: str) -> str:
        normalized_email = value.lower().strip()
        if CustomUser.objects.filter(email = normalized_email).exists():
            raise serializers.ValidationError("User with this email already exists")
        return normalized_email

    def create(self, validated_data: dict[str, str]) -> CustomUser:
        return CustomUser.objects.create_user(
            email = validated_data["email"],
            password = validated_data["password"]
        )
