(() => {
  document.querySelectorAll('input[type=file][data-max-bytes]').forEach(input => {
    input.addEventListener('change', () => {
      const limit = Number(input.dataset.maxBytes);
      input.setCustomValidity(input.files[0]?.size > limit ? `Choose a file smaller than ${Math.floor(limit / 1048576)} MiB.` : '');
      input.reportValidity();
    });
  });
})();
