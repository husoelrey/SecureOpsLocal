use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};

mod nginx;
mod ssh;
mod types;

#[pyfunction]
fn parse_ssh_line<'py>(py: Python<'py>, line: &str, current_year: i32) -> PyResult<Bound<'py, PyDict>> {
    let parsed = ssh::parse_ssh_line(line, current_year);
    parsed.to_py_dict(py)
}

#[pyfunction]
fn parse_ssh_file<'py>(
    py: Python<'py>,
    file_path: &str,
    current_year: i32,
) -> PyResult<Bound<'py, PyList>> {
    let parsed_list = ssh::parse_ssh_file(file_path, current_year).map_err(|e| {
        pyo3::exceptions::PyIOError::new_err(format!("Failed to read SSH log file: {}", e))
    })?;

    let py_list = PyList::empty_bound(py);
    for item in parsed_list {
        py_list.append(item.to_py_dict(py)?)?;
    }
    Ok(py_list)
}

#[pyfunction]
fn parse_nginx_line<'py>(
    py: Python<'py>,
    line: &str,
    current_year: i32,
) -> PyResult<Bound<'py, PyDict>> {
    let parsed = nginx::parse_nginx_line(line, current_year);
    parsed.to_py_dict(py)
}

#[pyfunction]
fn parse_nginx_file<'py>(
    py: Python<'py>,
    file_path: &str,
    current_year: i32,
) -> PyResult<Bound<'py, PyList>> {
    let parsed_list = nginx::parse_nginx_file(file_path, current_year).map_err(|e| {
        pyo3::exceptions::PyIOError::new_err(format!("Failed to read Nginx log file: {}", e))
    })?;

    let py_list = PyList::empty_bound(py);
    for item in parsed_list {
        py_list.append(item.to_py_dict(py)?)?;
    }
    Ok(py_list)
}

#[pymodule]
fn secureops_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(parse_ssh_line, m)?)?;
    m.add_function(wrap_pyfunction!(parse_ssh_file, m)?)?;
    m.add_function(wrap_pyfunction!(parse_nginx_line, m)?)?;
    m.add_function(wrap_pyfunction!(parse_nginx_file, m)?)?;
    Ok(())
}
