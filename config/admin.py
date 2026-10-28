from django.contrib.admin import AdminSite


class WeFilesAdminSite(AdminSite):
    site_header = "WeFiles maintenance"
    site_title = "WeFiles"
    index_title = "Maintenance tools"

    def has_permission(self, request):
        return super().has_permission(request) and request.user.approved


site = WeFilesAdminSite(name="admin")
