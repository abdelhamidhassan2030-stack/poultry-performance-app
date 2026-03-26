import io
from typing import Dict, Tuple

import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="مؤشر أداء دورة الدواجن", page_icon="🐔", layout="wide")

# =========================================================
# إعدادات أولية
# =========================================================
DEFAULT_REFERENCE = pd.DataFrame(
    {
        "العمر_يوم": [28, 30, 32, 35, 38, 40, 42],
        "الوزن_المرجعي_جرام": [1200, 1350, 1500, 1700, 1900, 2100, 2300],
    }
)

DEFAULT_RECOMMENDATIONS = {
    "ممتاز": [
        "الاستمرار على نفس برنامج الإدارة والتغذية.",
        "الحفاظ على جودة المياه والتهوية وعدم تغيير العلف دون سبب.",
        "الاستمرار في المتابعة اليومية وتسجيل الأوزان بانتظام.",
    ],
    "جيد": [
        "الاستمرار في البرنامج الحالي مع متابعة استهلاك العلف والمياه.",
        "مراجعة التهوية ودرجة الحرارة والتأكد من عدم وجود تزاحم.",
        "إعادة الوزن في الزيارة القادمة للتأكد من ثبات الأداء.",
    ],
    "يحتاج إلى تحسين": [
        "مراجعة جودة العلف وكميته والتأكد من وصوله لجميع الطيور.",
        "فحص مصادر المياه ونظافة السقايات والتأكد من عدم وجود نقص في الشرب.",
        "مراجعة التهوية ودرجة الحرارة والكثافة داخل المكان.",
        "مراجعة برنامج التحصين ومتابعة أي أعراض مرضية أو نفوق غير طبيعي.",
    ],
    "ضعيف": [
        "التدخل السريع بمراجعة العلف والمياه والتهوية والكثافة فورًا.",
        "إجراء زيارة بيطرية عاجلة لتقييم الحالة العامة للقطيع.",
        "مراجعة التاريخ المرضي والتحصينات والأدوية المستخدمة خلال الدورة.",
        "تحليل أسباب انخفاض الوزن مع مقارنة العمر الحالي بعدد الطيور النافقة ومستوى التجانس.",
    ],
}


# =========================================================
# دوال مساعدة
# =========================================================
def find_reference_weight(age_days: int, ref_df: pd.DataFrame) -> Tuple[float, str]:
    """Return nearest reference weight and note about exact/nearest match."""
    ref_df = ref_df.dropna().copy()
    ref_df["العمر_يوم"] = pd.to_numeric(ref_df["العمر_يوم"], errors="coerce")
    ref_df["الوزن_المرجعي_جرام"] = pd.to_numeric(ref_df["الوزن_المرجعي_جرام"], errors="coerce")
    ref_df = ref_df.dropna().sort_values("العمر_يوم")

    exact = ref_df[ref_df["العمر_يوم"] == age_days]
    if not exact.empty:
        return float(exact.iloc[0]["الوزن_المرجعي_جرام"]), "تم استخدام وزن مرجعي مطابق لنفس العمر."

    ref_df["distance"] = (ref_df["العمر_يوم"] - age_days).abs()
    nearest = ref_df.sort_values(["distance", "العمر_يوم"]).iloc[0]
    return float(nearest["الوزن_المرجعي_جرام"]), f"لا يوجد عمر مطابق تمامًا، فتم استخدام أقرب عمر مرجعي: {int(nearest['العمر_يوم'])} يوم."



def calculate_average_weight(input_mode: str, total_8_birds_weight: float, avg_bird_weight: float) -> float:
    if input_mode == "وزن 8 طيور معًا":
        return total_8_birds_weight / 8
    if input_mode == "متوسط وزن الطائر":
        return avg_bird_weight
    # الاثنين
    values = []
    if total_8_birds_weight and total_8_birds_weight > 0:
        values.append(total_8_birds_weight / 8)
    if avg_bird_weight and avg_bird_weight > 0:
        values.append(avg_bird_weight)
    if not values:
        return 0
    return sum(values) / len(values)



def calculate_performance(avg_weight: float, ref_weight: float) -> Dict:
    if ref_weight <= 0:
        return {
            "achievement_pct": 0.0,
            "gap_pct": 0.0,
            "rating": "غير محسوب",
            "indicator_text": "لا يمكن الحساب بدون وزن مرجعي صحيح.",
        }

    achievement_pct = (avg_weight / ref_weight) * 100
    gap_pct = ((avg_weight - ref_weight) / ref_weight) * 100

    if achievement_pct >= 100:
        rating = "ممتاز"
    elif achievement_pct >= 95:
        rating = "جيد"
    elif achievement_pct >= 85:
        rating = "يحتاج إلى تحسين"
    else:
        rating = "ضعيف"

    return {
        "achievement_pct": round(achievement_pct, 1),
        "gap_pct": round(gap_pct, 1),
        "rating": rating,
        "indicator_text": f"حقق القطيع {round(achievement_pct, 1)}% من الوزن المرجعي لعمر {ref_weight:.0f} جرام.",
    }



def generate_recommendations(rating: str, mortality_count: int = 0) -> list:
    recs = DEFAULT_RECOMMENDATIONS.get(rating, []).copy()
    if mortality_count > 0:
        recs.append("يوجد نفوق مسجل، لذلك يجب ربط تقييم الوزن بسبب النفوق والأعراض الإكلينيكية إن وجدت.")
    return recs



def convert_df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8-sig")


# =========================================================
# عنوان التطبيق
# =========================================================
st.title("🐔 تطبيق مؤشر أداء دورة الدواجن")
st.write(
    "نسخة أولى مبسطة: إدخال عمر الدورة ووزن الطيور، ثم حساب مؤشر الأداء مقارنة بالوزن المرجعي مع عرض التوصيات المناسبة."
)


# =========================================================
# الشريط الجانبي: تعديل جدول المرجع
# =========================================================
st.sidebar.header("إعدادات التقييم")
st.sidebar.write("يمكنك تعديل جدول الوزن المرجعي مباشرة من هنا حسب السلالة أو المرجع الذي تعمل به.")

reference_df = st.sidebar.data_editor(
    DEFAULT_REFERENCE,
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
    key="reference_table",
)

st.sidebar.markdown("### حدود التقييم الحالية")
st.sidebar.info(
    "ممتاز: 100% فأكثر\n\n"
    "جيد: من 95% إلى أقل من 100%\n\n"
    "يحتاج إلى تحسين: من 85% إلى أقل من 95%\n\n"
    "ضعيف: أقل من 85%"
)


# =========================================================
# الواجهة الرئيسية
# =========================================================
col1, col2 = st.columns([1.2, 1])

with col1:
    st.subheader("بيانات الزيارة")

    breeder_name = st.text_input("اسم المربية", placeholder="مثال: أم محمد")
    village_name = st.text_input("اسم القرية", placeholder="مثال: الكرم")
    visit_date = st.date_input("تاريخ الزيارة")

    age_days = st.number_input("عمر الدورة (يوم)", min_value=1, max_value=100, value=35, step=1)

    input_mode = st.radio(
        "طريقة إدخال الوزن",
        options=["وزن 8 طيور معًا", "متوسط وزن الطائر", "الاثنان معًا"],
        horizontal=True,
    )

    total_8_birds_weight = 0.0
    avg_bird_weight = 0.0

    if input_mode in ["وزن 8 طيور معًا", "الاثنان معًا"]:
        total_8_birds_weight = st.number_input(
            "وزن 8 طيور معًا (جرام)", min_value=0.0, value=13600.0, step=50.0
        )

    if input_mode in ["متوسط وزن الطائر", "الاثنان معًا"]:
        avg_bird_weight = st.number_input(
            "متوسط وزن الطائر (جرام)", min_value=0.0, value=1700.0, step=10.0
        )

    mortality_count = st.number_input("عدد النافق", min_value=0, value=0, step=1)
    birds_count = st.number_input("عدد الطيور الحالي", min_value=0, value=0, step=1)

    analyze_btn = st.button("احسب المؤشر", type="primary", use_container_width=True)

with col2:
    st.subheader("جدول الوزن المرجعي المستخدم")
    st.dataframe(reference_df, use_container_width=True, hide_index=True)


# =========================================================
# النتائج
# =========================================================
if analyze_btn:
    try:
        ref_weight, ref_note = find_reference_weight(age_days, pd.DataFrame(reference_df))
        avg_weight = calculate_average_weight(input_mode, total_8_birds_weight, avg_bird_weight)
        result = calculate_performance(avg_weight, ref_weight)
        recommendations = generate_recommendations(result["rating"], mortality_count)

        st.markdown("---")
        st.subheader("نتيجة التقييم")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("متوسط وزن الطائر", f"{avg_weight:.0f} جرام")
        m2.metric("الوزن المرجعي", f"{ref_weight:.0f} جرام")
        m3.metric("نسبة التحقيق", f"{result['achievement_pct']}%")
        m4.metric("التصنيف", result["rating"])

        if result["rating"] == "ممتاز":
            st.success(result["indicator_text"])
        elif result["rating"] == "جيد":
            st.info(result["indicator_text"])
        elif result["rating"] == "يحتاج إلى تحسين":
            st.warning(result["indicator_text"])
        else:
            st.error(result["indicator_text"])

        st.caption(ref_note)

        st.markdown("### تفسير سريع")
        if result["gap_pct"] >= 0:
            st.write(f"الوزن أعلى أو مساوي للمرجع بفارق {result['gap_pct']}%.")
        else:
            st.write(f"الوزن أقل من المرجع بفارق {abs(result['gap_pct'])}%.")

        st.markdown("### التوصيات")
        for i, rec in enumerate(recommendations, start=1):
            st.write(f"{i}. {rec}")

        summary_row = pd.DataFrame(
            [
                {
                    "اسم_المربية": breeder_name,
                    "القرية": village_name,
                    "تاريخ_الزيارة": visit_date,
                    "عمر_الدورة_يوم": age_days,
                    "طريقة_الإدخال": input_mode,
                    "وزن_8_طيور_معًا_جرام": total_8_birds_weight,
                    "متوسط_وزن_الطائر_جرام": round(avg_weight, 2),
                    "الوزن_المرجعي_جرام": ref_weight,
                    "نسبة_التحقيق": result["achievement_pct"],
                    "الفجوة_عن_المرجع_%": result["gap_pct"],
                    "التصنيف": result["rating"],
                    "عدد_النافق": mortality_count,
                    "عدد_الطيور_الحالي": birds_count,
                }
            ]
        )

        st.markdown("### سجل النتيجة")
        st.dataframe(summary_row, use_container_width=True, hide_index=True)

        st.download_button(
            "تنزيل النتيجة CSV",
            data=convert_df_to_csv_bytes(summary_row),
            file_name="poultry_cycle_performance_result.csv",
            mime="text/csv",
            use_container_width=True,
        )

    except Exception as e:
        st.error(f"حدث خطأ أثناء الحساب: {e}")


# =========================================================
# شرح المرحلة الحالية
# =========================================================
with st.expander("ما الذي تنفذه هذه النسخة؟"):
    st.write(
        "1) تسمح بإدخال عمر الدورة والوزن.\n"
        "2) تقارن الوزن بجدول مرجعي قابل للتعديل.\n"
        "3) تعطي تصنيفًا: ممتاز / جيد / يحتاج إلى تحسين / ضعيف.\n"
        "4) تعرض توصيات أولية قابلة للتطوير لاحقًا.\n"
        "5) تخرج سجلًا بسيطًا يمكن تنزيله."
    )

with st.expander("ما الذي سنضيفه في المرحلة التالية؟"):
    st.write(
        "- إدخال الوزن الفردي لـ 8 طيور بدل الوزن المجمع فقط.\n"
        "- حساب التجانس بين الطيور.\n"
        "- ربط التوصيات بنسبة النفوق والعمر ودرجة الانخفاض.\n"
        "- صفحة Dashboard مجمعة لكل الزيارات.\n"
        "- رفع ملف Excel فيه زيارات كثيرة وتحليلها دفعة واحدة."
    )
