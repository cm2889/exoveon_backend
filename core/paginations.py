from rest_framework.pagination import PageNumberPagination
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.pagination import BasePagination


class StandardPageNumberPagination(PageNumberPagination):
    """
    Custom pagination class that sets the default page size and maximum page size.
    """
    page_size = 10 
    max_page_size = 200
    page_query_param = 'page'
    page_size_query_param = 'size'
    last_page_strings = ('last',)


class StandardLimitPagination(LimitOffsetPagination):
    """ Custom pagination class that sets the default limit and maximum limit. """
    default_limit = 10 
    max_limit = 200
    limit_query_param = 'limit'
    offset_query_param = 'offset'


class DynamicPagination(BasePagination):
    """
    Custom pagination class that allows for dynamic pagination based on query parameters.
    """

    def paginate_queryset(self, queryset, request, view=None):
        pagination_type = request.query_params.get('pagination_type', 'page')

        if pagination_type == 'limit':
            self.paginator = StandardLimitPagination()
        else:
            self.paginator = StandardPageNumberPagination()

        return self.paginator.paginate_queryset(queryset, request, view)

    def get_paginated_response(self, data):
        return self.paginator.get_paginated_response(data)