(() => {
  document.querySelectorAll('.avatar-radio').forEach(input => {
    input.addEventListener('change', () => {
      const preview = document.querySelector('[data-avatar-preview]');
      const caption = document.querySelector('[data-avatar-caption]');
      if (!preview || !input.checked) return;
      const selectedArt = input.closest('.avatar-choice')?.querySelector('.avatar-option-body .avatar svg');
      if (selectedArt) preview.replaceChildren(selectedArt.cloneNode(true));
      preview.dataset.avatar = input.value;
      if (caption) caption.textContent = `Preview: ${input.dataset.avatarLabel}. Save changes to apply.`;
    });
  });
})();
