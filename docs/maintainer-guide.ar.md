# دليل المشرف: رفع تحديث جديد إلى GitHub

هذا الدليل لمن يصون المشروع. كل الأوامر تُشغَّل في الطرفية (fish).

## مرة واحدة فقط

```sh
sudo pacman -S --needed git github-cli python-pipx
gh auth login                      # اختر GitHub.com ثم HTTPS ثم المتصفح
git config --global user.name "الاسم"
git config --global user.email "البريد"
git clone https://github.com/mryujruu/caelestia-doctor ~/doctor-repo
```

## عند كل إصدار جديد

استبدل `<الرقم>` برقم الإصدار (مثل `0.6.0`) و`<الملف>` باسم ملف الـ zip.

```sh
cd ~/doctor-repo
git pull                                              # آخر نسخة من GitHub
unzip -o ~/Downloads/"<الملف>.zip" -d ~/Downloads/doctor-new
cp -r ~/Downloads/doctor-new/caelestia-doctor/. .     # النقطة الأخيرة مهمة
git status --short                                    # راجع التغييرات
grep version pyproject.toml                           # تأكد من الرقم
```

تأكد أن `git status` لا يذكر `.venv` ولا `__pycache__`، ثم جرّب النسخة على جهازك:

```sh
pipx install . --force
caelestia-doctor --version
caelestia-doctor
```

ثم انشرها:

```sh
git add .
git commit -m "v<الرقم>: وصف قصير"
git push
git tag v<الرقم>
git push origin v<الرقم>
awk '/^## <الرقم>/{f=1;next} /^## /{f=0} f' CHANGELOG.md > /tmp/notes.md
gh release create v<الرقم> --title "v<الرقم>" --notes-file /tmp/notes.md
rm -rf ~/Downloads/doctor-new
```

## ملاحظات

- النسخ فوق الريبو **يضيف ويستبدل** الملفات، ولا يحذف ما حُذف من النسخة الجديدة. لتطابق كامل ثبّت `rsync` واستعمل `rsync -a --delete --exclude='.git' ~/Downloads/doctor-new/caelestia-doctor/ ./` ثم راجع `git status --short` جيدًا.
- لا تستخدم `git push --force` إلا إذا كنت تعرف أثره.
- لا تعِد استخدام رقم إصدار منشور. إن وُجد الـ tag فغيّر الرقم.
- `Author identity unknown` يعني أنك لم تضبط `user.name` و`user.email`.
- إن رُفض `git push` فجرّب `git pull --rebase` ثم أعد الدفع.

## دالة fish اختيارية (لم تُجرَّب على جهاز فعلي)

تجمع الخطوات في أمر واحد. أنشئ `~/.config/fish/functions/doctor-release.fish`:

```fish
function doctor-release
    if test (count $argv) -ne 2
        echo "usage: doctor-release ZIP VERSION"
        return 1
    end
    set zip $argv[1]
    set ver $argv[2]

    cd ~/doctor-repo; or return 1
    git pull --ff-only; or return 1

    rm -rf /tmp/doc-new; and mkdir /tmp/doc-new; and unzip -q $zip -d /tmp/doc-new; or return 1
    test -d /tmp/doc-new/caelestia-doctor; or begin; echo "unexpected zip layout"; return 1; end
    cp -r /tmp/doc-new/caelestia-doctor/. .

    grep -q "version = \"$ver\"" pyproject.toml; or begin; echo "pyproject.toml is not version $ver"; return 1; end

    pipx install . --force; and caelestia-doctor --version; or return 1
    git status --short

    read -P "Commit and publish v$ver? [y/N] " ok
    test "$ok" = y; or return 1

    git add .; and git commit -m "v$ver"; and git push; or return 1
    git tag v$ver; and git push origin v$ver; or return 1
    awk "/^## $ver/{f=1;next} /^## /{f=0} f" CHANGELOG.md > /tmp/notes.md
    gh release create v$ver --title "v$ver" --notes-file /tmp/notes.md
end
```

الاستخدام: `doctor-release ~/Downloads/الملف.zip 0.6.0`
