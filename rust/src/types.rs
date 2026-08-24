use chrono::{DateTime, Datelike, Timelike, Utc};
use pyo3::prelude::*;
use pyo3::types::{PyDateTime, PyDict, PyTzInfo};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ParsedLogLine {
    pub timestamp: DateTime<Utc>,
    pub source_ip: Option<String>,
    pub user: Option<String>,
    pub event_type: String,
    pub port: Option<u32>,
    pub raw_content: String,
    pub is_parsed: bool,
}

impl ParsedLogLine {
    pub fn to_py_dict<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
        let dict = PyDict::new_bound(py);

        let datetime_mod = py.import_bound("datetime")?;
        let timezone_obj = datetime_mod.getattr("timezone")?;
        let utc_any = timezone_obj.getattr("utc")?;
        let utc_tz = utc_any.downcast::<PyTzInfo>()?;

        let py_dt = PyDateTime::new_bound(
            py,
            self.timestamp.year(),
            self.timestamp.month() as u8,
            self.timestamp.day() as u8,
            self.timestamp.hour() as u8,
            self.timestamp.minute() as u8,
            self.timestamp.second() as u8,
            self.timestamp.nanosecond() / 1_000,
            Some(utc_tz),
        )?;

        dict.set_item("timestamp", py_dt)?;
        dict.set_item("source_ip", &self.source_ip)?;
        dict.set_item("user", &self.user)?;
        dict.set_item("event_type", &self.event_type)?;
        dict.set_item("port", &self.port)?;
        dict.set_item("raw_content", &self.raw_content)?;
        dict.set_item("is_parsed", self.is_parsed)?;

        Ok(dict)
    }
}
