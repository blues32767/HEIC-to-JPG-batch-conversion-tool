import os
import sys
from pathlib import Path
from PIL import Image
import pillow_heif
from concurrent.futures import ThreadPoolExecutor, as_completed
import time


def convert_single_heic_thread(heic_file, quality, output_subfolder):
    """
    轉換單一HEIC檔案並輸出到子資料夾
    """
    start_time = time.time()

    try:
        image = Image.open(heic_file)
        if image.mode in ('RGBA', 'LA', 'P'):
            image = image.convert('RGB')

        # 建立輸出路徑
        if output_subfolder:
            output_dir = heic_file.parent / output_subfolder
            output_dir.mkdir(exist_ok=True)
            jpg_file = output_dir / (heic_file.stem + '.jpg')
        else:
            jpg_file = heic_file.with_suffix('.jpg')

        image.save(jpg_file, "JPEG", quality=quality, optimize=True)

        processing_time = time.time() - start_time
        return (heic_file.name, True, "", processing_time, str(jpg_file))

    except Exception as e:
        processing_time = time.time() - start_time
        return (heic_file.name, False, str(e), processing_time, "")


def heic_to_jpg_batch_multithread(folder_path, quality=90, max_workers=None, output_subfolder="jpg_output"):
    """
    多執行緒批次轉換，避免重複檔案
    """
    try:
        pillow_heif.register_heif_opener()

        folder = Path(folder_path)
        if not folder.exists() or not folder.is_dir():
            print(f"錯誤：資料夾 {folder_path} 不存在")
            return False

        # 尋找所有HEIC檔案
        all_heic_files = []
        for ext in ['*.heic', '*.HEIC']:
            all_heic_files.extend(folder.glob(ext))

        # 去除重複檔案（基於檔名前綴，不區分大小寫）
        seen_stems = set()
        unique_heic_files = []

        for file in all_heic_files:
            stem_lower = file.stem.lower()
            if stem_lower not in seen_stems:
                seen_stems.add(stem_lower)
                unique_heic_files.append(file)
            else:
                print(f"跳過重複檔案: {file.name}")

        heic_files = unique_heic_files

        if not heic_files:
            print("未找到HEIC檔案")
            return False

        if max_workers is None:
            max_workers = min(os.cpu_count(), len(heic_files), 8)

        # 顯示資訊
        if len(all_heic_files) != len(heic_files):
            print(f"找到 {len(all_heic_files)} 個HEIC檔案（含重複）")
            print(f"去除重複後: {len(heic_files)} 個檔案")
        else:
            print(f"找到 {len(heic_files)} 個HEIC檔案")

        if output_subfolder:
            output_path = folder / output_subfolder
            print(f"JPG檔案將輸出到: {output_path}")
        else:
            print("JPG檔案將輸出到相同資料夾")

        print(f"使用多執行緒處理，工作者數量: {max_workers}")
        print("-" * 60)

        start_time = time.time()
        converted_count = 0
        failed_files = []
        total_processing_time = 0

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任務
            future_to_file = {
                executor.submit(convert_single_heic_thread, heic_file, quality, output_subfolder): heic_file
                for heic_file in heic_files
            }

            # 處理完成的任務
            for i, future in enumerate(as_completed(future_to_file), 1):
                filename, success, error, proc_time, output_file = future.result()
                total_processing_time += proc_time

                if success:
                    output_name = Path(output_file).name if output_file else filename.replace('.heic', '.jpg').replace(
                        '.HEIC', '.jpg')
                    print(f"[{i:2d}/{len(heic_files)}] ✓ {filename} → {output_name} ({proc_time:.2f}秒)")
                    converted_count += 1
                else:
                    print(f"[{i:2d}/{len(heic_files)}] ✗ {filename} - 錯誤: {error}")
                    failed_files.append(filename)

        total_time = time.time() - start_time

        print("-" * 60)
        print(f"轉換完成！")
        print(f"成功: {converted_count}張，失敗: {len(failed_files)}張")
        print(f"總耗時: {total_time:.2f}秒")
        print(f"平均每張: {total_time / len(heic_files):.2f}秒")
        if total_processing_time > 0:
            print(f"加速比: {total_processing_time / total_time:.1f}x")

        if output_subfolder:
            print(f"JPG檔案已儲存在: {folder / output_subfolder}")

        return True

    except Exception as e:
        print(f"程式執行錯誤: {str(e)}")
        return False


def heic_to_jpg_batch_single(folder_path, quality=90, output_subfolder=None):
    """
    單執行緒版本，避免重複檔案
    """
    try:
        pillow_heif.register_heif_opener()

        folder = Path(folder_path)
        if not folder.exists() or not folder.is_dir():
            print(f"錯誤：資料夾 {folder_path} 不存在")
            return False

        # 尋找並去重
        all_heic_files = []
        for ext in ['*.heic', '*.HEIC']:
            all_heic_files.extend(folder.glob(ext))

        seen_stems = set()
        unique_heic_files = []

        for file in all_heic_files:
            stem_lower = file.stem.lower()
            if stem_lower not in seen_stems:
                seen_stems.add(stem_lower)
                unique_heic_files.append(file)
            else:
                print(f"跳過重複檔案: {file.name}")

        heic_files = unique_heic_files

        if not heic_files:
            print("未找到HEIC檔案")
            return False

        if len(all_heic_files) != len(heic_files):
            print(f"找到 {len(all_heic_files)} 個HEIC檔案（含重複）")
            print(f"去除重複後: {len(heic_files)} 個檔案")
        else:
            print(f"找到 {len(heic_files)} 個HEIC檔案，使用單執行緒轉換...")

        print("-" * 60)

        start_time = time.time()
        converted_count = 0

        # 建立輸出資料夾
        if output_subfolder:
            output_dir = folder / output_subfolder
            output_dir.mkdir(exist_ok=True)

        for i, heic_file in enumerate(heic_files, 1):
            try:
                file_start = time.time()
                image = Image.open(heic_file)
                if image.mode in ('RGBA', 'LA', 'P'):
                    image = image.convert('RGB')

                if output_subfolder:
                    jpg_file = output_dir / (heic_file.stem + '.jpg')
                else:
                    jpg_file = heic_file.with_suffix('.jpg')

                image.save(jpg_file, "JPEG", quality=quality, optimize=True)
                file_time = time.time() - file_start

                print(f"[{i:2d}/{len(heic_files)}] ✓ {heic_file.name} → {jpg_file.name} ({file_time:.2f}秒)")
                converted_count += 1

            except Exception as e:
                print(f"[{i:2d}/{len(heic_files)}] ✗ {heic_file.name} - 錯誤: {str(e)}")

        total_time = time.time() - start_time
        print("-" * 60)
        print(f"轉換完成！成功: {converted_count}張，總耗時: {total_time:.2f}秒")
        return True

    except Exception as e:
        print(f"程式執行錯誤: {str(e)}")
        return False


def main():
    """主程式 - 簡化版"""
    print("=" * 60)
    print("        HEIC轉JPG批次轉換工具")
    print("=" * 60)

    while True:
        try:
            print("\n請選擇轉換速度:")
            print("1. 🐌 慢速模式 - 一次轉一張，穩定可靠")
            print("2. 🚀 快速模式 - 一次轉多張，速度快 (推薦)")
            print("3. 🤖 智慧模式 - 讓程式自動選擇最適合的速度")
            print("4. ❌ 退出程式")

            choice = input("\n請選擇 (1-4): ").strip()

            if choice in ["1", "2", "3"]:
                folder_path = input("請輸入HEIC照片資料夾路徑: ").strip().strip('"')
                if not folder_path:
                    if getattr(sys, 'frozen', False):
                        folder_path = Path(sys.executable).parent
                    else:
                        folder_path = Path(__file__).parent
                    print(f"使用程式所在目錄: {folder_path}")

                print("\n請選擇JPG檔案輸出位置:")
                print("1. 與HEIC檔案放在同一個資料夾")
                print("2. 放在子資料夾中 (推薦，比較整齊)")

                output_choice = input("請選擇 (1-2，預設2): ").strip()

                if output_choice == "1":
                    output_subfolder = None
                else:
                    subfolder_name = input("請輸入子資料夾名稱 (預設 'jpg_output'): ").strip()
                    output_subfolder = subfolder_name if subfolder_name else "jpg_output"

                quality = input("\n請輸入JPG品質 (1-95，預設90): ").strip()
                try:
                    quality = int(quality) if quality else 90
                    quality = max(1, min(95, quality))
                except ValueError:
                    quality = 90

                if choice == "1":
                    # 慢速模式
                    heic_to_jpg_batch_single(str(folder_path), quality, output_subfolder)
                elif choice == "2":
                    # 快速模式
                    workers = input("請輸入工作者數量 (預設自動): ").strip()
                    try:
                        max_workers = int(workers) if workers else None
                    except ValueError:
                        max_workers = None
                    heic_to_jpg_batch_multithread(str(folder_path), quality, max_workers, output_subfolder)
                elif choice == "3":
                    # 智慧模式
                    file_count = len(list(Path(folder_path).glob('*.heic')) +
                                     list(Path(folder_path).glob('*.HEIC')))
                    if file_count > 10:
                        print("偵測到多個檔案，使用快速模式")
                        heic_to_jpg_batch_multithread(str(folder_path), quality, None, output_subfolder)
                    else:
                        print("偵測到少量檔案，使用慢速模式")
                        heic_to_jpg_batch_single(str(folder_path), quality, output_subfolder)

            elif choice == "4":
                print("程式結束，謝謝使用！")
                break

            else:
                print("無效的選擇，請重新輸入")

        except KeyboardInterrupt:
            print("\n\n程式被使用者中斷")
            break
        except Exception as e:
            print(f"發生錯誤: {str(e)}")

    input("\n按Enter鍵退出...")


if __name__ == "__main__":
    main()
