(() => {
  document.querySelectorAll('[data-copy-template-button]').forEach((button) => {
    const template = document.getElementById(button.getAttribute('aria-controls'));
    const status = document.querySelector('[data-copy-template-status]');
    if (!template || !status) return;
    button.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(template.value);
        status.textContent = 'Copied. Replace the bracketed details before using the template.';
      } catch (_) {
        template.focus();
        template.select();
        status.textContent = 'The template is selected. Copy it using your browser or keyboard.';
      }
    });
  });
})();
