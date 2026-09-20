"""Custom friendly error handlers."""
from django.shortcuts import render


def handler400(request, exception=None):
    return render(request, "errors/400.html", status=400)


def handler401(request, exception=None):
    return render(request, "errors/401.html", status=401)


def handler403(request, exception=None):
    return render(request, "errors/403.html", status=403)


def handler404(request, exception=None):
    return render(request, "errors/404.html", status=404)


def handler500(request):
    return render(request, "errors/500.html", status=500)