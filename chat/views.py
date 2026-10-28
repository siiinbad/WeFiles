from django.contrib import messages
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.views import View

from core.access import ApprovedMixin
from core.services import rate_limit

from .forms import MessageForm
from .models import ChatMessage
from .services import send_message


def conversation(request):
    page = Paginator(ChatMessage.objects.select_related("sender"), 50).get_page(
        request.GET.get("page")
    )
    return {
        "messages_page": page,
        "chat_messages": list(reversed(page.object_list)),
        "form": MessageForm(),
    }


class ChatView(ApprovedMixin, View):
    def get(self, request):
        return render(request, "chat/room.html", conversation(request))


class MessageListView(ApprovedMixin, View):
    def get(self, request):
        context = conversation(request)
        latest = str(context["chat_messages"][-1].pk) if context["chat_messages"] else ""
        if request.headers.get("X-WeFiles-Latest") == latest and request.headers.get(
            "X-WeFiles-Count"
        ) == str(context["messages_page"].paginator.count):
            return HttpResponse(status=204)
        return render(request, "chat/messages.html", context)


@method_decorator(rate_limit("chat", limit=20, seconds=60), name="dispatch")
class MessageCreateView(ApprovedMixin, View):
    def post(self, request):
        form = MessageForm(request.POST)
        if form.is_valid():
            send_message(request.user, form.cleaned_data["content"])
            messages.success(request, "Message sent.")
            return redirect("chat:room")
        return render(
            request, "chat/room.html", {**conversation(request), "form": form}, status=400
        )
