package com.licenta.repository;

import com.licenta.model.Project;

import org.springframework.data.jpa.repository.JpaRepository;


public interface ProjectRepository extends JpaRepository<Project, Long> {

}