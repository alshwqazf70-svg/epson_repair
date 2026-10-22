/* موسوعة إبسون الاحترافية — سلوك الواجهة (بدون اعتماديات خارجية) */
(function () {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    /* قائمة الهاتف */
    var toggle = document.querySelector(".nav-toggle");
    var nav = document.querySelector(".main-nav");
    if (toggle && nav) {
      toggle.addEventListener("click", function () {
        var open = nav.classList.toggle("open");
        toggle.setAttribute("aria-expanded", open ? "true" : "false");
      });
    }

    /* تكبير الصور */
    var items = document.querySelectorAll("[data-lightbox]");
    if (items.length) {
      var box = document.createElement("div");
      box.className = "lightbox";
      box.innerHTML = '<button class="close" type="button" aria-label="إغلاق">&times;</button><img alt="">';
      document.body.appendChild(box);
      var img = box.querySelector("img");
      box.querySelector(".close").addEventListener("click", function () {
        box.classList.remove("open");
      });
      box.addEventListener("click", function (e) {
        if (e.target === box) box.classList.remove("open");
      });
      items.forEach(function (el) {
        el.addEventListener("click", function () {
          img.src = el.getAttribute("data-lightbox");
          img.alt = el.getAttribute("data-title") || "";
          box.classList.add("open");
        });
      });
      document.addEventListener("keydown", function (e) {
        if (e.key === "Escape") box.classList.remove("open");
      });
    }

    /* تأكيد عمليات الحذف */
    document.querySelectorAll("form[data-confirm]").forEach(function (form) {
      form.addEventListener("submit", function (e) {
        if (!window.confirm(form.getAttribute("data-confirm"))) {
          e.preventDefault();
        }
      });
    });

    /* تحديد كل الأعراض / إلغاؤها */
    var selectAll = document.querySelector("[data-select-all]");
    if (selectAll) {
      selectAll.addEventListener("click", function () {
        var boxes = document.querySelectorAll("input[name='symptoms']");
        var allChecked = Array.prototype.every.call(boxes, function (b) { return b.checked; });
        boxes.forEach(function (b) { b.checked = !allChecked; });
      });
    }

    /* طباعة الصفحة */
    var printBtn = document.querySelector("[data-print]");
    if (printBtn) {
      printBtn.addEventListener("click", function () { window.print(); });
    }
  });
})();
