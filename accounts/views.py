from django.contrib.auth import login
from django.shortcuts import render, redirect
from .forms import RegisterForm


def register(request):
    if request.user.is_authenticated:
        return redirect('classrooms:dashboard')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('classrooms:dashboard')
    else:
        form = RegisterForm()

    return render(request, 'accounts/register.html', {'form': form})
