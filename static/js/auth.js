/**
 * SafeAnesthesia Infusomat Propofol Module
 * GESTIÓN DE AUTENTICACIÓN FRONTEND (AJAX SECURE)
 */

document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.querySelector('form');
    if (!loginForm) return;

    loginForm.addEventListener('submit', async (e) => {
        // Si el formulario procesa directo por POST tradicional no interviene
        // Pero para dar una experiencia de UX premium con SPA interceptamos y mostramos spinner/alertas
        e.preventDefault();

        const usernameInput = document.getElementById('username');
        const passwordInput = document.getElementById('password');
        const rememberInput = document.getElementById('remember');

        const payload = {
            username: usernameInput.value,
            password: passwordInput.value,
            remember: rememberInput ? rememberInput.checked : false
        };

        const submitBtn = loginForm.querySelector('button');
        const originalText = submitBtn.innerText;
        submitBtn.disabled = true;
        submitBtn.innerText = "Accediendo...";

        // Eliminar errores anteriores
        const oldError = document.querySelector('.login-error');
        if (oldError) oldError.remove();

        try {
            const response = await fetch('/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });

            const result = await response.json();
            if (response.ok && result.success) {
                // Redirigir al panel principal
                window.location.href = '/';
            } else {
                showError(result.message || 'Error al iniciar sesión.');
            }
        } catch (error) {
            console.error('Error de autenticación:', error);
            showError('Error de red o servidor no disponible.');
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerText = originalText;
        }
    });

    function showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'login-error';
        errorDiv.innerText = message;
        loginForm.after(errorDiv);
    }
});
