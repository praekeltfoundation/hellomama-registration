from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import CursorPagination
from rest_framework import viewsets
from .models import Record, State
from .serializers import StateSerializer


class IdCursorPagination(CursorPagination):
    ordering = 'id'


class RecordPost(APIView):

    """ Webhook listener for identities needing a unique ID
    """
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        """ Accepts and creates a new unique ID record
        """
        if "id" in request.data["data"]:
            rec = {
                "identity": request.data["data"]["id"]
            }
            if "details" in request.data["data"] and \
                    "uniqueid_field_name" in request.data["data"]["details"]:
                rec["write_to"] = \
                    request.data["data"]["details"]["uniqueid_field_name"]
            else:
                rec["write_to"] = "health_id"
            if "details" in request.data["data"] and \
                    "uniqueid_field_length" in request.data["data"]["details"]:
                rec["length"] = \
                    request.data["data"]["details"]["uniqueid_field_length"]
            Record.objects.create(**rec)
            # Return
            status = 201
            accepted = {"accepted": True}
            return Response(accepted, status=status)
        else:
            # Return
            status = 400
            accepted = {"id": ['This field is required.']}
            return Response(accepted, status=status)


class StateGetViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows States to be viewed.
    """
    permission_classes = (IsAuthenticated,)
    queryset = State.objects.all()
    pagination_class = IdCursorPagination
    serializer_class = StateSerializer
