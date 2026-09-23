from django.shortcuts import render


def error_404(request, exception=None):
    return render(request, "404.html", status=404)


def error_403(request, exception=None):
    return render(request, "403.html", status=403)
