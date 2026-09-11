(function () {
  'use strict';

  function ready(callback) {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', callback);
    } else {
      callback();
    }
  }

  ready(function () {
    var input = document.getElementById('mgsdq-logo');
    var selectButton = document.getElementById('mgs-dq-select-logo');
    var removeButton = document.getElementById('mgs-dq-remove-logo');
    var preview = document.getElementById('mgs-dq-logo-preview');
    var frame;

    function renderPreview(url) {
      if (!preview || !removeButton) return;
      preview.replaceChildren();
      if (url) {
        var image = document.createElement('img');
        image.src = url;
        image.alt = 'Logo selecionado';
        preview.appendChild(image);
        preview.classList.add('has-image');
        removeButton.hidden = false;
        return;
      }

      var icon = document.createElement('span');
      icon.className = 'dashicons dashicons-format-image';
      var label = document.createElement('span');
      label.textContent = 'Nenhum logo selecionado';
      preview.append(icon, label);
      preview.classList.remove('has-image');
      removeButton.hidden = true;
    }

    if (input && selectButton && removeButton && preview) {
      selectButton.addEventListener('click', function () {
        if (typeof wp === 'undefined' || !wp.media) return;
        if (!frame) {
          frame = wp.media({
            title: 'Escolher logo do site',
            button: { text: 'Usar este logo' },
            library: { type: 'image' },
            multiple: false
          });
          frame.on('select', function () {
            var attachment = frame.state().get('selection').first().toJSON();
            input.value = attachment.url || '';
            renderPreview(input.value);
            input.dispatchEvent(new Event('change', { bubbles: true }));
          });
        }
        frame.open();
      });

      removeButton.addEventListener('click', function () {
        input.value = '';
        renderPreview('');
        input.dispatchEvent(new Event('change', { bubbles: true }));
      });

      input.addEventListener('change', function () {
        renderPreview(input.value.trim());
      });
    }

    Array.prototype.forEach.call(document.querySelectorAll('.mgs-dq-select-category-image'), function (button) {
      button.addEventListener('click', function () {
        if (typeof wp === 'undefined' || !wp.media) return;
        var target = document.getElementById(button.getAttribute('data-target') || '');
        if (!target) return;
        var categoryFrame = wp.media({
          title: 'Escolher imagem da categoria',
          button: { text: 'Usar esta imagem' },
          library: { type: 'image' },
          multiple: false
        });
        categoryFrame.on('select', function () {
          var attachment = categoryFrame.state().get('selection').first().toJSON();
          target.value = attachment.url || '';
          target.dispatchEvent(new Event('change', { bubbles: true }));
        });
        categoryFrame.open();
      });
    });

    var layout = document.getElementById('mgsdq-layout');
    var v3Fields = document.querySelector('[data-mgs-dq-model-fields="lp3"]');
    function syncModelFields() {
      if (!layout || !v3Fields) return;
      v3Fields.hidden = layout.value !== 'lp3';
    }
    if (layout && v3Fields) {
      layout.addEventListener('change', syncModelFields);
      syncModelFields();
    }
  });
}());
