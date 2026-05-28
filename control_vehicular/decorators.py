from functools import wraps
from typing import Callable

from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect


def rol_requerido(*roles_permitidos: str) -> Callable:
    def decorador(view_func: Callable) -> Callable:
        @wraps(view_func)
        @login_required(login_url='/login/')
        def wrapper(request: HttpRequest, *args: object, **kwargs: object) -> HttpResponse:
            perfil = getattr(request.user, 'perfil', None)
            if perfil is None or perfil.rol not in roles_permitidos:
                return HttpResponseForbidden('Acceso denegado: no tienes permisos para esta operación.')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorador


def admin_required(view_func: Callable) -> Callable:
    return rol_requerido('ADMIN')(view_func)


def staff_required(view_func: Callable) -> Callable:
    return rol_requerido('ADMIN', 'MECANICO')(view_func)


class RolRequiredMixin(LoginRequiredMixin):
    login_url = '/login/'
    roles_permitidos: tuple[str, ...] = ()

    def dispatch(self, request: HttpRequest, *args: object, **kwargs: object) -> HttpResponse:
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        perfil = getattr(request.user, 'perfil', None)
        if perfil is None or perfil.rol not in self.roles_permitidos:
            return HttpResponseForbidden('Acceso denegado: no tienes permisos para esta operación.')
        return super().dispatch(request, *args, **kwargs)


class AdminRequiredMixin(RolRequiredMixin):
    roles_permitidos = ('ADMIN',)


class StaffRequiredMixin(RolRequiredMixin):
    roles_permitidos = ('ADMIN', 'MECANICO')
